"""Severity bands for anomaly flags, in one place.

Payment and meal flags are scored on different scales, so they need their own
bands:

* Payment flags come straight from the payment Isolation Forest. It flags a
  transaction once its score passes 0.50, and in practice its flags score
  between about 0.50 and 0.65, so the meal bands below would label every real
  payment flag LOW. Payment bands therefore sit on the model's own scale.
* Meal flags usually come from the explainable rules, which score 0.80 to 0.90,
  while model-only meal flags score just above 0.50.
"""
from django.db.models import Q

PAYMENT_MEDIUM, PAYMENT_HIGH = 0.55, 0.60
MEAL_MEDIUM, MEAL_HIGH = 0.65, 0.80


def _level(score, medium, high):
    if score >= high:
        return 'HIGH'
    if score >= medium:
        return 'MEDIUM'
    return 'LOW'


def payment_severity(score):
    return _level(score, PAYMENT_MEDIUM, PAYMENT_HIGH)


def meal_severity(score):
    return _level(score, MEAL_MEDIUM, MEAL_HIGH)


def _filter(level, medium, high, field):
    if level == 'HIGH':
        return Q(**{f'{field}__gte': high})
    if level == 'MEDIUM':
        return Q(**{f'{field}__gte': medium, f'{field}__lt': high})
    if level == 'LOW':
        return Q(**{f'{field}__lt': medium})
    return Q()


def payment_filter(level, field='anomaly_score'):
    """ORM filter for payment flags of one severity level (any level if unknown)."""
    return _filter(level, PAYMENT_MEDIUM, PAYMENT_HIGH, field)


def meal_filter(level, field='anomaly_score'):
    return _filter(level, MEAL_MEDIUM, MEAL_HIGH, field)
