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


class TestRegisterEnforcesValidators(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name='PW School', county='Nairobi', contact_email='pw@test.com')

    def _register(self, password):
        return self.client.post('/api/auth/register/', {
            'full_name': 'New Parent', 'email': 'newparent@example.com',
            'password': password, 'role': 'parent',
            'school_id': self.school.id,
        }, content_type='application/json')

    def test_common_password_blocked_at_registration(self):
        res = self._register('password123')
        self.assertEqual(res.status_code, 400)
        self.assertIn('password', res.json())

    def test_numeric_password_blocked_at_registration(self):
        self.assertEqual(self._register('4829175630').status_code, 400)

    def test_strong_password_registers(self):
        self.assertEqual(self._register('Tr1cky-Meadow-Lamp').status_code, 201)
