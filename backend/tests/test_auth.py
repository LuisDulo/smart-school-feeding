import pytest
from django.test import TestCase
from meals.models import School, User, MealAccount
import bcrypt


def make_hashed(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


@pytest.fixture
def school(db):
    return School.objects.create(
        name='Test Primary',
        county='Nairobi',
        contact_email='test@school.co.ke'
    )


@pytest.fixture
def student_user(db, school):
    user = User.objects.create(
        school=school,
        role='student',
        full_name='Test Student',
        email='student@test.com',
        hashed_password=make_hashed('Password123!')
    )
    MealAccount.objects.create(student=user, balance_cents=50000)
    return user


@pytest.fixture
def client():
    from django.test import Client
    return Client()


class TestRegister(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name='Test School', county='Nairobi',
            contact_email='school@test.com')

    def test_register_student_creates_meal_account(self):
        response = self.client.post('/api/auth/register/', {
            'full_name': 'Jane Kamau',
            'email': 'jane@test.com',
            'password': 'Password123!',
            'role': 'student',
            'school_id': self.school.id
        }, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            MealAccount.objects.filter(
                student__email='jane@test.com').exists())

    def test_register_duplicate_email_fails(self):
        User.objects.create(
            school=self.school, role='student',
            full_name='Existing', email='exists@test.com',
            hashed_password=make_hashed('pass'))
        response = self.client.post('/api/auth/register/', {
            'full_name': 'New User',
            'email': 'exists@test.com',
            'password': 'Password123!',
            'role': 'student',
            'school_id': self.school.id
        }, content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_register_parent_does_not_create_meal_account(self):
        response = self.client.post('/api/auth/register/', {
            'full_name': 'Parent User',
            'email': 'parent@test.com',
            'password': 'Password123!',
            'role': 'parent',
            'school_id': self.school.id
        }, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertFalse(
            MealAccount.objects.filter(
                student__email='parent@test.com').exists())


class TestLogin(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name='Test School', county='Nairobi',
            contact_email='login@test.com')
        self.user = User.objects.create(
            school=self.school, role='bursar',
            full_name='Bursar Test', email='bursar@test.com',
            hashed_password=make_hashed('Password123!'))

    def test_login_returns_tokens(self):
        response = self.client.post('/api/auth/login/', {
            'email': 'bursar@test.com',
            'password': 'Password123!'
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.json()['tokens'])
        self.assertIn('refresh', response.json()['tokens'])

    def test_wrong_password_returns_401(self):
        response = self.client.post('/api/auth/login/', {
            'email': 'bursar@test.com',
            'password': 'WrongPassword!'
        }, content_type='application/json')
        self.assertEqual(response.status_code, 401)

    def test_nonexistent_email_returns_401(self):
        response = self.client.post('/api/auth/login/', {
            'email': 'nobody@test.com',
            'password': 'Password123!'
        }, content_type='application/json')
        self.assertEqual(response.status_code, 401)


class TestProfile(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name='Test School', county='Nairobi',
            contact_email='profile@test.com')
        self.user = User.objects.create(
            school=self.school, role='admin',
            full_name='Admin User', email='admin@test.com',
            hashed_password=make_hashed('Password123!'))

    def test_profile_requires_token(self):
        response = self.client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, 401)

    def test_profile_returns_user_data_with_token(self):
        login = self.client.post('/api/auth/login/', {
            'email': 'admin@test.com',
            'password': 'Password123!'
        }, content_type='application/json')
        token = login.json()['tokens']['access']
        response = self.client.get(
            '/api/auth/profile/',
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['email'], 'admin@test.com')
        self.assertEqual(response.json()['role'], 'admin')
