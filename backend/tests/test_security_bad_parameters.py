"""
Malformed query parameters crashed endpoints with a 500, and the super admin
report window had no upper bound.
"""
import bcrypt
from django.test import TestCase

from meals.models import MealAccount, School, User


PASSWORD = 'Tr1cky-Passw0rd!'


def hashed(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


class TestMalformedParameters(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name='Param School', county='Nairobi', contact_email='p@test.com')
        student = User.objects.create(
            school=self.school, role='student', full_name='Param Student',
            email='pstudent@test.com', hashed_password=hashed(PASSWORD))
        MealAccount.objects.create(student=student, balance_cents=1000)
        User.objects.create(school=self.school, role='parent', full_name='Param Parent',
                            email='pparent@test.com', hashed_password=hashed(PASSWORD))
        User.objects.create(school=self.school, role='superadmin', full_name='Param Super',
                            email='psuper@test.com', hashed_password=hashed(PASSWORD))

    def auth(self, email):
        login = self.client.post('/api/auth/login/', {'email': email, 'password': PASSWORD},
                                 content_type='application/json')
        return {'HTTP_AUTHORIZATION': f"Bearer {login.json()['tokens']['access']}"}

    def test_non_numeric_months_and_days_are_bad_requests(self):
        auth = self.auth('pstudent@test.com')
        for url in ('/api/payments/monthly-report/?months=abc',
                    '/api/payments/balance-trend/?days=abc'):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url, **auth).status_code, 400)

    def test_non_numeric_meal_account_id_is_not_found(self):
        auth = self.auth('pparent@test.com')
        for url in ('/api/payments/balance/?meal_account_id=abc',
                    '/api/payments/activity/?meal_account_id=abc',
                    '/api/meals/qr/?meal_account_id=abc'):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url, **auth).status_code, 404)

    def test_super_admin_report_days_are_validated(self):
        auth = self.auth('psuper@test.com')
        for days in ('abc', '100000000'):
            with self.subTest(days=days):
                response = self.client.get(f'/api/superadmin/analytics/?days={days}', **auth)
                self.assertEqual(response.status_code, 400)
