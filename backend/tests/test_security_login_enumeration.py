"""
Login answered faster for an unknown email than for a wrong password, which
told an attacker which emails have accounts.
"""
from unittest.mock import patch

import bcrypt
from django.test import TestCase

from meals.models import School, User


PASSWORD = 'Tr1cky-Passw0rd!'


def hashed(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


class TestLoginDoesNotRevealAccounts(TestCase):
    def setUp(self):
        school = School.objects.create(
            name='Login School', county='Nairobi', contact_email='l@test.com')
        User.objects.create(school=school, role='parent', full_name='Known Parent',
                            email='known@test.com', hashed_password=hashed(PASSWORD))

    def login(self, email):
        return self.client.post('/api/auth/login/',
                                {'email': email, 'password': 'wrong-password'},
                                content_type='application/json')

    def test_unknown_email_still_runs_a_password_check(self):
        # Equal work for both cases is what makes the timing equal.
        with patch('accounts.views.bcrypt.checkpw', wraps=bcrypt.checkpw) as check:
            unknown = self.login('nobody@test.com')
            known = self.login('known@test.com')
        self.assertEqual(check.call_count, 2)
        self.assertEqual(unknown.status_code, known.status_code)
        self.assertEqual(unknown.json(), known.json())
