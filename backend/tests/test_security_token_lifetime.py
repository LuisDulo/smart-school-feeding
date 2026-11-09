"""
Access tokens lived for 12 hours and could not be revoked, so a stolen one
kept working after logout. They now last 15 minutes and the clients refresh.
"""
from datetime import timedelta

from django.test import TestCase
from rest_framework_simplejwt.settings import api_settings


class TestAccessTokenLifetime(TestCase):
    def test_access_tokens_are_short_lived(self):
        self.assertLessEqual(api_settings.ACCESS_TOKEN_LIFETIME, timedelta(minutes=30))
