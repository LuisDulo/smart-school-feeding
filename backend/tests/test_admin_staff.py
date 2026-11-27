"""
School administrators can create kitchen and bursar accounts for their own
school, so hiring a cook no longer needs the super administrator. They cannot
create administrator accounts, and the usual account rules still apply.
"""
import bcrypt
from django.test import TestCase

from meals.models import School, User

PASSWORD = 'Tr1cky-Meadow-Lamp'
URL = '/api/auth/admin/staff/'


def make_user(school, role, name, email):
    return User.objects.create(
        school=school, role=role, full_name=name, email=email,
        hashed_password=bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt()).decode())


class TestAdminCreatesStaff(TestCase):
    def setUp(self):
        self.school = School.objects.create(name='Staff School', county='Nairobi',
                                            contact_email='staff@test.com')
        self.other = School.objects.create(name='Other Staff School', county='Nairobi',
                                           contact_email='other.staff@test.com')
        make_user(self.school, 'admin', 'Staff Admin', 'admin@staff.test')
        make_user(self.school, 'bursar', 'Staff Bursar', 'bursar@staff.test')
        make_user(self.other, 'kitchen', 'Other Cook', 'cook@other.test')

    def token(self, email):
        return self.client.post('/api/auth/login/', {'email': email, 'password': PASSWORD},
                                content_type='application/json').json()['tokens']['access']

    def post(self, body, email='admin@staff.test'):
        return self.client.post(URL, body, content_type='application/json',
                                HTTP_AUTHORIZATION=f'Bearer {self.token(email)}')

    def test_admin_creates_kitchen_and_bursar_accounts_in_their_school(self):
        for role, email in (('kitchen', 'new.cook@staff.test'), ('bursar', 'new.bursar@staff.test')):
            res = self.post({'full_name': f'New {role}', 'email': email,
                             'password': PASSWORD, 'role': role})
            self.assertEqual(res.status_code, 201, res.content)
            user = User.objects.get(email=email)
            self.assertEqual((user.role, user.school_id), (role, self.school.id))
        # the new kitchen account can sign in and reach the serving endpoint
        cook = self.token('new.cook@staff.test')
        self.assertEqual(self.client.get('/api/meals/lookup/?q=ab',
                                         HTTP_AUTHORIZATION=f'Bearer {cook}').status_code, 200)

    def test_admin_cannot_create_administrators_or_other_roles(self):
        for role in ('admin', 'superadmin', 'parent', 'student'):
            res = self.post({'full_name': 'Nope', 'email': f'{role}@nope.test',
                             'password': PASSWORD, 'role': role})
            self.assertEqual(res.status_code, 400, role)
            self.assertIn('role', res.json())
        self.assertFalse(User.objects.filter(email__endswith='@nope.test').exists())

    def test_password_rules_and_duplicate_emails_apply(self):
        res = self.post({'full_name': 'Weak', 'email': 'weak@staff.test',
                         'password': 'password123', 'role': 'kitchen'})
        self.assertEqual(res.status_code, 400)
        self.assertIn('password', res.json())
        res = self.post({'full_name': 'Copy', 'email': 'bursar@staff.test',
                         'password': PASSWORD, 'role': 'kitchen'})
        self.assertEqual(res.status_code, 400)
        self.assertIn('email', res.json())

    def test_list_shows_only_this_schools_staff(self):
        res = self.client.get(URL, HTTP_AUTHORIZATION=f'Bearer {self.token("admin@staff.test")}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual({s['email'] for s in res.json()},
                         {'admin@staff.test', 'bursar@staff.test'})

    def test_only_school_admins_can_manage_staff(self):
        res = self.post({'full_name': 'Sneaky', 'email': 'sneaky@staff.test',
                         'password': PASSWORD, 'role': 'kitchen'}, email='bursar@staff.test')
        self.assertEqual(res.status_code, 403)
        self.assertFalse(User.objects.filter(email='sneaky@staff.test').exists())
