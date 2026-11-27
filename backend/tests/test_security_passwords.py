from django.test import TestCase
from meals.models import School
from accounts.password_rules import password_problems


class TestPasswordRules(TestCase):
    def test_common_password_rejected(self):
        self.assertTrue(password_problems('password123'))

    def test_numeric_only_rejected(self):
        self.assertTrue(password_problems('4829175630'))

    def test_password_similar_to_email_rejected(self):
        self.assertTrue(password_problems(
            'amina.wanjiru', 'Amina Wanjiru', 'amina.wanjiru@example.com'))

    def test_strong_password_accepted(self):
        self.assertEqual(
            password_problems('Tr1cky-Meadow-Lamp', 'Amina Wanjiru',
                              'amina@example.com'), [])


class TestAccountCreationEnforcesValidators(TestCase):
    """Accounts are created by school administrators, so that is where the
    password rules must hold."""

    def setUp(self):
        import bcrypt
        from meals.models import User
        self.school = School.objects.create(
            name='PW School', county='Nairobi', contact_email='pw@test.com')
        User.objects.create(
            school=self.school, role='admin', full_name='PW Admin', email='admin@pw.test',
            hashed_password=bcrypt.hashpw(b'Tr1cky-Meadow-Lamp', bcrypt.gensalt()).decode())
        self.token = self.client.post(
            '/api/auth/login/', {'email': 'admin@pw.test', 'password': 'Tr1cky-Meadow-Lamp'},
            content_type='application/json').json()['tokens']['access']

    def _create_parent(self, password):
        return self.client.post('/api/auth/admin/parents/', {
            'full_name': 'New Parent', 'email': 'newparent@example.com',
            'password': password,
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {self.token}')

    def test_common_password_blocked_at_account_creation(self):
        res = self._create_parent('password123')
        self.assertEqual(res.status_code, 400)
        self.assertIn('password', res.json())

    def test_numeric_password_blocked_at_account_creation(self):
        self.assertEqual(self._create_parent('4829175630').status_code, 400)

    def test_strong_password_creates_the_account(self):
        self.assertEqual(self._create_parent('Tr1cky-Meadow-Lamp').status_code, 201)
