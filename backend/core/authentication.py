from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken

from meals.models import User


class MealsJWTAuthentication(JWTAuthentication):
    """
    Our access/refresh tokens carry a `user_id` claim pointing at a row in
    meals.User — a plain business-logic table, separate from Django's
    AUTH_USER_MODEL (django.contrib.auth.User, used only for /admin/ login).

    The stock JWTAuthentication.get_user() resolves that claim against
    get_user_model() and checks `user.is_active`, neither of which apply to
    meals.User. This override resolves it against the correct table instead,
    so request.user on any authenticated API view is a meals.User instance.
    """

    def get_user(self, validated_token):
        user_id = validated_token.get('user_id')
        if user_id is None:
            raise InvalidToken('Token contained no recognizable user identification')

        try:
            return User.objects.select_related('school').get(id=user_id)
        except User.DoesNotExist:
            raise AuthenticationFailed('User not found', code='user_not_found')
