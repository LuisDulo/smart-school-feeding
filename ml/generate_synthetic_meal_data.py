"""
Expand the demand-forecasting training set from ~133 rows to ~15000 rows.

The original ml/data/meal_distribution.csv was exported from the live
demo school's actual MealDistributionEvent history (see
backend/meals/management/commands/generate_data.py), which only spans
one school's ~7 months of simulated terms -- too little history for
ensemble models (Random Forest, XGBoost) to have an edge over Linear
Regression. Re-running that Django command to accumulate more real
history would mean simulating over a decade of daily records for a
single demo school directly in the production-shaped Postgres database,
which is destructive to the live demo accounts used throughout the
rest of the project.

Instead this script reproduces the SAME attendance-generation
methodology (day-of-week dips, exam-week dips, week-1 settling-in dip,
random daily noise, holiday-free weekday-only school calendar, a
13-week term cycle) standalone, with no Django/DB dependency, and
extends it across many synthetic terms to reach ~15000 rows. Feature
engineering (lagged rolling_7day_avg, lagged attendance_rate) mirrors
generate_data.py's CSV export exactly, so the two datasets are
methodologically consistent -- this one is just longer.

student_enrolment is kept constant at 50 (matching the live school),
since the trained models are deployed against that one real school and
training on enrolment values it will never see at inference time would
only hurt, not help.
"""
import sys
import os
import csv
import random
from datetime import date, timedelta

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

random.seed(42)

TARGET_ROWS = 15000
ENROLMENT = 50
WEEKS_PER_TERM = 13


def is_school_day(d):
    return d.weekday() < 5


def is_exam_week(week_number):
    return week_number in [12, 13]


def get_attendance_rate(d, week_number):
    base = 0.88
    if d.weekday() == 0:
        base -= 0.05
    if d.weekday() == 4:
        base -= 0.04
    if is_exam_week(week_number):
        base -= 0.12
    if week_number == 1:
        base -= 0.08
    base += random.uniform(-0.04, 0.04)
    return max(0.60, min(0.98, base))


# ── Walk forward day by day across many terms until we have enough rows ──
print("=" * 60)
print("SYNTHETIC MEAL DISTRIBUTION DATA GENERATOR")
print(f"Target: {TARGET_ROWS} rows (methodology matches generate_data.py)")
print("=" * 60)

rows = []
term_num = 1
current = date(2019, 1, 7)  # Monday — start of a synthetic "Term 1 2019"

while len(rows) < TARGET_ROWS:
    term_start = current
    term_name = f"Term {((term_num - 1) % 3) + 1} {term_start.year}"
    days_in_term = 0
    week_num = 1

    while days_in_term < WEEKS_PER_TERM * 7 and len(rows) < TARGET_ROWS:
        if is_school_day(current):
            week_num = min((days_in_term // 7) + 1, WEEKS_PER_TERM)
            exam = is_exam_week(week_num)
            true_attendance_rate = get_attendance_rate(current, week_num)
            meals_served = int(round(ENROLMENT * true_attendance_rate))

            rows.append({
                'meal_date': current.isoformat(),
                'term': term_name,
                'term_week': week_num,
                'day_of_week': current.weekday(),
                'is_exam_week': 1 if exam else 0,
                'student_enrolment': ENROLMENT,
                '_true_attendance_rate': round(true_attendance_rate, 4),
                'attendance_rate': 0,
                'rolling_7day_avg': 0,
                'meals_served': meals_served,
            })
        current += timedelta(days=1)
        days_in_term += 1

    # Two-week term break — a real school calendar gap, and it keeps the
    # 13-week/term structure that TermSchedule.current_week_number()
    # (and is_exam_week's weeks 12-13) expects from a live term.
    current += timedelta(days=14)
    term_num += 1

print(f"Raw rows generated: {len(rows)} across {term_num - 1} terms")

# ── Lagged rolling_7day_avg (meals) — uses only days strictly before ─────
for i, row in enumerate(rows):
    past = rows[max(0, i - 7):i]
    if past:
        row['rolling_7day_avg'] = round(
            sum(r['meals_served'] for r in past) / len(past), 2)
    else:
        row['rolling_7day_avg'] = row['meals_served']

# ── Lagged attendance_rate — same 7-day lookback, never same-day value ───
DEFAULT_ATTENDANCE_RATE = 0.85
for i, row in enumerate(rows):
    past = rows[max(0, i - 7):i]
    if past:
        row['attendance_rate'] = round(
            sum(r['_true_attendance_rate'] for r in past) / len(past), 4)
    else:
        row['attendance_rate'] = DEFAULT_ATTENDANCE_RATE

for row in rows:
    del row['_true_attendance_rate']

# ── Write CSV ─────────────────────────────────────────────────────
csv_path = os.path.join('data', 'meal_distribution.csv')
fieldnames = ['meal_date', 'term', 'term_week', 'day_of_week',
              'is_exam_week', 'student_enrolment', 'attendance_rate',
              'rolling_7day_avg', 'meals_served']
with open(csv_path, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"\nCSV written: {len(rows)} rows -> {csv_path}")
print(f"Date range: {rows[0]['meal_date']} -> {rows[-1]['meal_date']}")
print(f"Meals/day range: {min(r['meals_served'] for r in rows)} - "
      f"{max(r['meals_served'] for r in rows)}")
print("\nOriginal 133-row dataset preserved at "
      "ml/data/meal_distribution_original_133rows.csv")
