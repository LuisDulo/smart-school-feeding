import bcrypt
from django.test import TestCase

from meals.models import School, User

PASSWORD = 'Tr1cky-Meadow-Lamp'


def make_hashed(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


class TestModelComparisonAccess(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name='MC School', county='Nairobi', contact_email='mc@test.com')
        self.network = School.objects.create(
            name='Webmasters Kenya', county='Nairobi', contact_email='wk@test.com')
        for school, role, email in (
            (self.school, 'admin', 'mcadmin@test.com'),
            (self.school, 'bursar', 'mcbursar@test.com'),
            (self.school, 'kitchen', 'mckitchen@test.com'),
            (self.network, 'superadmin', 'mcsuper@test.com'),
        ):
            User.objects.create(school=school, role=role, full_name=role.title(),
                                email=email, hashed_password=make_hashed(PASSWORD))

    def _get(self, email):
        login = self.client.post('/api/auth/login/', {
            'email': email, 'password': PASSWORD}, content_type='application/json')
        token = login.json()['tokens']['access']
        return self.client.get('/api/forecast/models/',
                               HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_school_roles_are_forbidden(self):
        for email in ('mcadmin@test.com', 'mcbursar@test.com', 'mckitchen@test.com'):
            self.assertEqual(self._get(email).status_code, 403, email)

    def test_super_admin_can_view_the_comparison(self):
        res = self._get('mcsuper@test.com')
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIn('default_model', body)
        self.assertIn('comparison', body)

    def test_anonymous_is_rejected(self):
        self.assertEqual(self.client.get('/api/forecast/models/').status_code, 401)
