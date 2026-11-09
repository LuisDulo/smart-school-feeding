from rest_framework.exceptions import ValidationError


def int_param(request, name, default, low, high, clamp=False):
    """
    A whole-number query parameter between low and high.

    A value that is not a whole number is a 400, never a 500. A number
    outside the range is a 400 too, unless clamp is set, in which case it is
    pulled into the range (for endpoints that always clamped).
    """
    raw = request.query_params.get(name)
    if raw is None or raw == '':
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValidationError({name: 'Must be a whole number.'})
    if clamp:
        return max(low, min(value, high))
    if not low <= value <= high:
        raise ValidationError({name: f'Must be between {low} and {high}.'})
    return value
