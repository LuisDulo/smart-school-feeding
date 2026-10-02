from django.test import TestCase
from meals.models import School


class TestPublicRegistrationRoles(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name='Reg School', county='Nairobi', contact_email='reg@test.com')

    def _register(self, role):
        return self.client.post('/api/auth/register/', {
            'full_name': 'Some Person', 'email': f'{role}@reg.example.com',
            'password': 'Tr1cky-Meadow-Lamp', 'role': role,
            'school_id': self.school.id,
        }, content_type='application/json')

    def test_staff_roles_cannot_self_register(self):
        for role in ('admin', 'bursar', 'kitchen', 'superadmin'):
            res = self._register(role)
            self.assertEqual(res.status_code, 400, role)
            self.assertIn('role', res.json())

    def test_parent_and_student_can_register(self):
        for role in ('parent', 'student'):
            self.assertEqual(self._register(role).status_code, 201, role)
