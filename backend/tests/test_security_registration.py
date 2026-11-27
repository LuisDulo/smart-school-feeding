"""
Public self-registration let anyone on the internet add a student (or parent)
to any school by choosing its id. Accounts are now created only by a school
administrator, inside the administrator's own school, so the public endpoint
is gone for every role.
"""
import bcrypt
from django.test import TestCase

from meals.models import MealAccount, School, User

PASSWORD = 'Tr1cky-Meadow-Lamp'


def make_user(school, role, name, email):
    return User.objects.create(
        school=school, role=role, full_name=name, email=email,
        hashed_password=bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt()).decode())


class TestNoPublicRegistration(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name='Reg School', county='Nairobi', contact_email='reg@test.com')

    def test_no_role_can_register_itself(self):
        for role in ('parent', 'student', 'admin', 'bursar', 'kitchen', 'superadmin'):
            res = self.client.post('/api/auth/register/', {
                'full_name': 'Some Person', 'email': f'{role}@reg.example.com',
                'password': PASSWORD, 'role': role, 'school_id': self.school.id,
            }, content_type='application/json')
            self.assertEqual(res.status_code, 404, role)
        self.assertFalse(User.objects.filter(email__endswith='@reg.example.com').exists())


class TestAdminCreatesAccounts(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name='Admin School', county='Nairobi', contact_email='adm@test.com')
        self.other = School.objects.create(
            name='Other School', county='Nairobi', contact_email='other@test.com')
        make_user(self.school, 'admin', 'School Admin', 'admin@adm.test')
        make_user(self.school, 'parent', 'A Parent', 'parent@adm.test')

    def post(self, url, email, body):
        token = self.client.post('/api/auth/login/', {'email': email, 'password': PASSWORD},
                                 content_type='application/json').json()['tokens']['access']
        return self.client.post(url, body, content_type='application/json',
                                HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_admin_creates_a_student_in_their_own_school(self):
        res = self.post('/api/auth/admin/students/', 'admin@adm.test', {
            'full_name': 'New Student', 'email': 'new.student@adm.test', 'password': PASSWORD})
        self.assertEqual(res.status_code, 201)
        student = User.objects.get(email='new.student@adm.test')
        self.assertEqual((student.role, student.school_id), ('student', self.school.id))
        self.assertTrue(MealAccount.objects.filter(student=student).exists())

    def test_admin_creates_a_parent_linked_to_their_child(self):
        self.post('/api/auth/admin/students/', 'admin@adm.test', {
            'full_name': 'Child', 'email': 'child@adm.test', 'password': PASSWORD})
        child = User.objects.get(email='child@adm.test')
        res = self.post('/api/auth/admin/parents/', 'admin@adm.test', {
            'full_name': 'New Parent', 'email': 'new.parent@adm.test', 'password': PASSWORD,
            'student_ids': [child.id]})
        self.assertEqual(res.status_code, 201)
        parent = User.objects.get(email='new.parent@adm.test')
        self.assertEqual((parent.role, parent.school_id), ('parent', self.school.id))
        self.assertTrue(child.meal_account.guardians.filter(id=parent.id).exists())

    def test_duplicate_email_is_rejected(self):
        res = self.post('/api/auth/admin/parents/', 'admin@adm.test', {
            'full_name': 'Copy', 'email': 'parent@adm.test', 'password': PASSWORD})
        self.assertEqual(res.status_code, 400)
        self.assertIn('email', res.json())

    def test_a_parent_cannot_create_accounts(self):
        res = self.post('/api/auth/admin/students/', 'parent@adm.test', {
            'full_name': 'Sneaky', 'email': 'sneaky@adm.test', 'password': PASSWORD})
        self.assertEqual(res.status_code, 403)
        self.assertFalse(User.objects.filter(email='sneaky@adm.test').exists())
