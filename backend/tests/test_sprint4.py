from django.test import TestCase
from meals.models import School, User, MealAccount, MealDistributionEvent
from datetime import date
import bcrypt


def make_hashed(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


class TestMealDistribution(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name='S4 School', county='Nairobi',
            contact_email='s4@test.com')
        self.student = User.objects.create(
            school=self.school, role='student',
            full_name='Test Student', email='s4student@test.com',
            hashed_password=make_hashed('Password123!'))
        self.meal_account = MealAccount.objects.create(
            student=self.student, balance_cents=100000)
        self.kitchen = User.objects.create(
            school=self.school, role='kitchen',
            full_name='Kitchen Staff', email='s4kitchen@test.com',
            hashed_password=make_hashed('Password123!'))

        login = self.client.post('/api/auth/login/', {
            'email': 's4kitchen@test.com',
            'password': 'Password123!'
        }, content_type='application/json')
        self.token = login.json()['tokens']['access']

    def test_record_meal_deducts_balance(self):
        response = self.client.post(
            '/api/meals/serve/',
            {'student_id': self.student.id},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        self.assertEqual(response.status_code, 201)
        self.meal_account.refresh_from_db()
        self.assertEqual(self.meal_account.balance_cents, 95000)

    def test_cannot_serve_meal_twice_same_day(self):
        self.client.post(
            '/api/meals/serve/',
            {'student_id': self.student.id},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        response = self.client.post(
            '/api/meals/serve/',
            {'student_id': self.student.id},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        self.assertEqual(response.status_code, 409)

    def test_insufficient_balance_rejected(self):
        self.meal_account.balance_cents = 1000
        self.meal_account.save()
        response = self.client.post(
            '/api/meals/serve/',
            {'student_id': self.student.id},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        self.assertEqual(response.status_code, 402)

    def test_student_lookup_returns_eligibility(self):
        response = self.client.get(
            f'/api/meals/lookup/?id={self.student.id}',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        self.assertEqual(response.status_code, 200)
        student_data = response.json()['students'][0]
        self.assertTrue(student_data['eligible'])
        self.assertEqual(student_data['balance_ksh'], 1000.0)

    def test_distribution_log_returns_todays_events(self):
        MealDistributionEvent.objects.create(
            meal_account=self.meal_account,
            recorded_by=self.kitchen,
            meal_date=date.today(),
            meals_served=1
        )
        login = self.client.post('/api/auth/login/', {
            'email': 's4kitchen@test.com',
            'password': 'Password123!'
        }, content_type='application/json')
        admin_token = login.json()['tokens']['access']
        response = self.client.get(
            '/api/meals/log/',
            HTTP_AUTHORIZATION=f'Bearer {admin_token}'
        )
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(
            response.json()['total_meals_served'], 1)
