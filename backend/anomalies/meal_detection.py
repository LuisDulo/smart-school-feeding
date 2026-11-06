"""
Anomaly detection for meal serving.

The top-up detector (anomalies/views.py) only scores M-Pesa payments. This
module covers the serving counter, where misuse would actually happen:

  * an Isolation Forest scores every served meal on five features
    (cost, hour, weekday, how many meals that student has had that day, and how
    far the cost is from that student's usual);
  * explainable rules catch the cases a reviewer should always see
    (outside serving hours, a non-school day, a meal far costlier than usual);
  * blocked attempts to serve past the daily limit are recorded, and repeated
    attempts for one student, or by one member of staff, raise a flag.

Every flag carries human-readable `reasons`, so a reviewer can see why.
The same feature code feeds live scoring, the scan command and model training
(ml/train_meal_anomaly_model.py), so all three agree.
"""
import logging
import os
from datetime import date, timedelta

import joblib
import numpy as np
import pandas as pd
from django.conf import settings
from django.db.models import Avg, Q
from django.utils import timezone

from meals.models import (BlockedServeAttempt, MealAnomalyFlag,
                          MealDistributionEvent)

logger = logging.getLogger(__name__)

FEATURES = [
    'amount_cents',
    'hour_of_day',
    'day_of_week',
    'meals_that_day',
    'amount_deviation',
]

SCHOOL_HOURS = (6, 17)        # a meal recorded before 06:00 or from 17:00 is unusual
COST_MULTIPLE = 3.0           # a meal this many times the student's usual ...
COST_MIN_CENTS = 15000        # ... and at least KES 150 is flagged
REPEAT_ATTEMPT_LIMIT = 2      # blocked attempts for one student in a day
STAFF_ATTEMPT_LIMIT = 5       # blocked attempts by one staff member in a day

SCORE_OFF_HOURS = 0.80
SCORE_NON_SCHOOL_DAY = 0.80
SCORE_COST = 0.85
SCORE_REPEAT_BASE = 0.75
SCORE_STAFF = 0.90

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, '..', 'ml', 'models', 'meal_isolation_forest.joblib')
SCALER_PATH = os.path.join(BASE_DIR, '..', 'ml', 'models', 'scaler_meal.joblib')

_model_cache = {}


def load_model():
    """Return (model, scaler), or (None, None) if the model files are missing."""
    if 'pair' not in _model_cache:
        try:
            _model_cache['pair'] = (joblib.load(MODEL_PATH), joblib.load(SCALER_PATH))
            logger.info('Meal anomaly model loaded.')
        except Exception as exc:
            logger.warning('Meal anomaly model not available (%s); rules only.', exc)
            _model_cache['pair'] = (None, None)
    return _model_cache['pair']


def ksh(cents):
    return f'KES {cents / 100:,.0f}'


# --------------------------------------------------------------------------
# Features
# --------------------------------------------------------------------------

def build_feature_frame(events=None):
    """One row per meal event, oldest first, with the model features.

    `events` is a queryset (default: every event). Pass a school's full
    history, not just a recent window, because "this student's usual cost"
    and "meals that day" look back at earlier events.
    """
    if events is None:
        events = MealDistributionEvent.objects.all()
    rows = list(events.order_by('created_at', 'id').values(
        'id', 'meal_account_id', 'recorded_by_id', 'created_at',
        'amount_cents', 'meal_date'))
    columns = ['event_id', 'meal_account_id', 'recorded_by_id', 'created_at',
               'amount_cents', 'meal_date', 'hour_of_day', 'time_label',
               'day_of_week', 'meals_that_day', 'amount_deviation', 'usual_cents']
    if not rows:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(rows).rename(columns={'id': 'event_id'})
    local = (pd.to_datetime(df['created_at'], utc=True)
             .dt.tz_convert(settings.TIME_ZONE))
    df['hour_of_day'] = local.dt.hour
    df['time_label'] = local.dt.strftime('%H:%M')
    df['day_of_week'] = pd.to_datetime(df['meal_date']).dt.weekday
    df['meals_that_day'] = df.groupby(['meal_account_id', 'meal_date']).cumcount() + 1

    by_account = df.groupby('meal_account_id')['amount_cents']
    prior_count = by_account.cumcount()
    prior_sum = by_account.cumsum() - df['amount_cents']
    prior_mean = prior_sum / prior_count.where(prior_count > 0)
    df['usual_cents'] = prior_mean
    df['amount_deviation'] = (
        (df['amount_cents'] - prior_mean).abs() / prior_mean.clip(lower=1)
    ).fillna(0.0).round(4)
    return df[columns]


def features_for_event(event):
    """The same features for one event, via a few small queries (live path)."""
    earlier = MealDistributionEvent.objects.filter(
        meal_account_id=event.meal_account_id
    ).filter(Q(created_at__lt=event.created_at)
             | Q(created_at=event.created_at, id__lt=event.id))
    meals_that_day = earlier.filter(meal_date=event.meal_date).count() + 1
    usual = earlier.aggregate(avg=Avg('amount_cents'))['avg']
    deviation = (abs(event.amount_cents - usual) / max(usual, 1)) if usual else 0.0
    local = timezone.localtime(event.created_at)
    return pd.DataFrame([{
        'event_id': event.id,
        'meal_account_id': event.meal_account_id,
        'recorded_by_id': event.recorded_by_id,
        'created_at': event.created_at,
        'amount_cents': event.amount_cents,
        'meal_date': event.meal_date,
        'hour_of_day': local.hour,
        'time_label': local.strftime('%H:%M'),
        'day_of_week': event.meal_date.weekday(),
        'meals_that_day': meals_that_day,
        'amount_deviation': round(deviation, 4),
        'usual_cents': usual if usual else np.nan,
    }])


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------

def _rule_hits(row):
    """Explainable rules -> list of (reason, score)."""
    hits = []
    hour = int(row['hour_of_day'])
    if hour < SCHOOL_HOURS[0] or hour >= SCHOOL_HOURS[1]:
        hits.append((
            f"Meal recorded at {row['time_label']}, outside school serving "
            f"hours ({SCHOOL_HOURS[0]:02d}:00-{SCHOOL_HOURS[1]:02d}:00)",
            SCORE_OFF_HOURS))
    if int(row['day_of_week']) >= 5:
        day = 'Saturday' if int(row['day_of_week']) == 5 else 'Sunday'
        hits.append((f'Meal recorded on a {day}, when there are no school meals',
                     SCORE_NON_SCHOOL_DAY))
    usual = row['usual_cents']
    if (pd.notna(usual) and usual > 0
            and row['amount_cents'] >= COST_MIN_CENTS
            and row['amount_cents'] >= COST_MULTIPLE * usual):
        hits.append((
            f"Meal cost {ksh(row['amount_cents'])} is "
            f"{row['amount_cents'] / usual:.1f}x this student's usual "
            f"{ksh(usual)}", SCORE_COST))
    return hits


def _model_reason(z_scores, model_score):
    """Plain-language reason for a model-only flag, from the standout features."""
    names = {
        'amount_cents': 'a higher meal cost than usual',
        'meals_that_day': "an extra meal for the student that day",
        'amount_deviation': "a cost far from this student's usual",
    }
    standouts = [names[f] for f, z in zip(FEATURES, z_scores)
                 if f in names and abs(z) >= 2.0]
    if standouts:
        return (f"Unusual meal pattern: {', '.join(standouts)} "
                f"(model score {model_score:.2f})")
    return ('Unusual combination of cost, timing and meals that day '
            f'(model score {model_score:.2f})')


def evaluate_frame(df):
    """Score every row. Returns a list of dicts: event_id, flag, score, reasons."""
    if df.empty:
        return []
    model, scaler = load_model()
    model_scores = np.zeros(len(df))
    model_flags = np.zeros(len(df), dtype=bool)
    z_matrix = np.zeros((len(df), len(FEATURES)))
    if model is not None:
        X = df[FEATURES].to_numpy(dtype=float)
        scaled = scaler.transform(X)
        raw = model.decision_function(scaled)
        model_scores = np.clip(1 - (raw + 0.5), 0, 1).round(4)
        model_flags = model.predict(scaled) == -1
        z_matrix = scaled

    results = []
    for i, (_, row) in enumerate(df.iterrows()):
        hits = _rule_hits(row)
        reasons = [reason for reason, _ in hits]
        scores = [score for _, score in hits]
        if model_flags[i]:
            scores.append(float(model_scores[i]))
            if not hits:
                reasons.append(_model_reason(z_matrix[i], float(model_scores[i])))
        flagged = bool(hits) or bool(model_flags[i])
        results.append({
            'event_id': int(row['event_id']),
            'flag': flagged,
            'score': round(max(scores), 4) if scores else float(model_scores[i]),
            'reasons': reasons,
        })
    return results


def evaluate_event(event):
    return evaluate_frame(features_for_event(event))[0]


# --------------------------------------------------------------------------
# Raising flags
# --------------------------------------------------------------------------

def _create_flag(event, result):
    account = event.meal_account
    flag, _ = MealAnomalyFlag.objects.get_or_create(
        meal_event=event,
        defaults=dict(
            school=account.student.school, meal_account=account,
            recorded_by=event.recorded_by, kind='pattern',
            flag_date=event.meal_date, anomaly_score=result['score'],
            reasons=result['reasons']))
    return flag


def flag_meal_event(event):
    """Score one just-served meal and raise a flag if it looks unusual."""
    result = evaluate_event(event)
    return _create_flag(event, result) if result['flag'] else None


def scan_events(school=None, days=30, dry_run=False, today=None):
    """Score existing meals of the last `days` days and flag the unusual ones.

    Already-flagged meals are skipped. Returns counts for the caller to show.
    """
    today = today or date.today()
    start = today - timedelta(days=days)
    events = MealDistributionEvent.objects.all()
    if school is not None:
        events = events.filter(meal_account__student__school=school)
    frame = build_feature_frame(events)
    if frame.empty:
        return {'scanned': 0, 'flagged': 0}
    already = set(MealAnomalyFlag.objects.filter(meal_event__isnull=False)
                  .values_list('meal_event_id', flat=True))
    window = frame[(pd.to_datetime(frame['meal_date']).dt.date >= start)
                   & ~frame['event_id'].isin(already)]
    results = [r for r in evaluate_frame(window) if r['flag']]
    if not dry_run and results:
        by_id = {e.id: e for e in MealDistributionEvent.objects.filter(
            id__in=[r['event_id'] for r in results]
        ).select_related('meal_account__student__school', 'recorded_by')}
        for result in results:
            _create_flag(by_id[result['event_id']], result)
    return {'scanned': len(window), 'flagged': len(results)}


def _upsert_attempt_flag(lookup, kind, school, meal_account, recorded_by,
                         today, score, reasons):
    flag, created = MealAnomalyFlag.objects.get_or_create(
        kind=kind, flag_date=today, meal_event=None, **lookup,
        defaults=dict(school=school, meal_account=meal_account,
                      recorded_by=recorded_by, anomaly_score=score,
                      reasons=reasons))
    if not created and not flag.reviewed:
        flag.anomaly_score = score
        flag.reasons = reasons
        flag.save(update_fields=['anomaly_score', 'reasons'])
    return flag


def record_blocked_attempt(meal_account, recorded_by, reason='daily_limit',
                           today=None):
    """Log a refused serve and raise flags when attempts keep repeating."""
    today = today or date.today()
    BlockedServeAttempt.objects.create(
        meal_account=meal_account, recorded_by=recorded_by,
        reason=reason, attempt_date=today)
    school = meal_account.student.school
    name = meal_account.student.full_name

    student_attempts = BlockedServeAttempt.objects.filter(
        meal_account=meal_account, attempt_date=today).count()
    if student_attempts >= REPEAT_ATTEMPT_LIMIT:
        _upsert_attempt_flag(
            {'meal_account': meal_account}, 'repeat_attempts', school,
            meal_account, recorded_by, today,
            min(0.95, SCORE_REPEAT_BASE + 0.05 * (student_attempts - REPEAT_ATTEMPT_LIMIT)),
            [f'{name} was refused a meal {student_attempts} times today after '
             f'reaching the daily limit'])

    if recorded_by is not None:
        staff_attempts = BlockedServeAttempt.objects.filter(
            recorded_by=recorded_by, attempt_date=today).count()
        if staff_attempts >= STAFF_ATTEMPT_LIMIT:
            _upsert_attempt_flag(
                {'meal_account': None, 'recorded_by': recorded_by},
                'staff_attempts', school, None, recorded_by, today,
                SCORE_STAFF,
                [f'{recorded_by.full_name} tried to serve past the daily limit '
                 f'{staff_attempts} times today'])
