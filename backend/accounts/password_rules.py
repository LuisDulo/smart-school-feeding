from types import SimpleNamespace

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import FieldDoesNotExist, ValidationError as DjangoValidationError
from rest_framework import serializers


class _NoFieldsMeta:
    def get_field(self, name):
        raise FieldDoesNotExist(name)


def password_problems(raw, full_name='', email=''):
    """Run the AUTH_PASSWORD_VALIDATORS from settings against a raw password.

    Returns a list of human-readable problems (empty if the password is OK).
    Our User model is not Django's, so the user-attribute similarity check is
    fed a small stand-in carrying the name/email fields it looks at.
    """
    first_name, _, last_name = (full_name or '').partition(' ')
    candidate = SimpleNamespace(
        username=(email or '').split('@')[0],
        first_name=first_name,
        last_name=last_name,
        email=email or '',
        _meta=_NoFieldsMeta(),
    )
    try:
        validate_password(raw, user=candidate)
    except DjangoValidationError as exc:
        return list(exc.messages)
    return []


def validate_password_or_raise(raw, full_name='', email=''):
    problems = password_problems(raw, full_name, email)
    if problems:
        raise serializers.ValidationError({'password': problems})
