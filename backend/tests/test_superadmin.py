from django.test import TestCase
from meals.models import (School, User, MealAccount,
                           PaymentTransaction, AnomalyFlag)
import bcrypt


def make_hashed(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def get_token(client, email, password='Password123!'):
    res = client.post('/api/auth/login/', {
        'email': email, 'password': password
    }, content_type='application/json')
    return res.json()['tokens']['access']


class TestSuperAdmin(TestCase):
    def setUp(self):
        # Webmasters Kenya org
        self.wk = School.objects.create(
            name='Webmasters Kenya',
            county='Nairobi',
            contact_email='admin@wk.co.ke')

        # Superadmin
        self.sa = User.objects.create(
            school=self.wk,
            role='superadmin',
            full_name='Super Admin',
            email='sa@wk.co.ke',
            hashed_password=make_hashed('Password123!'))
        self.token = get_token(self.client, 'sa@wk.co.ke')

        # Two test schools
        self.school1 = School.objects.create(
            name='School One', county='Nairobi',
            contact_email='s1@test.com')
        self.school2 = School.objects.create(
            name='School Two', county='Mombasa',
            contact_email='s2@test.com')

        # Students in each school
        for school in [self.school1, self.school2]:
            for i in range(5):
                student = User.objects.create(
                    school=school, role='student',
                    full_name=f'Student {i} {school.name}',
                    email=f'stu{i}@{school.id}.test',
                    hashed_password=make_hashed('Password123!'))
                MealAccount.objects.create(
                    student=student,
                    balance_cents=50000)

    def test_overview_returns_all_schools(self):
        res = self.client.get(
            '/api/superadmin/overview/',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['summary']['total_schools'], 2)
        self.assertEqual(data['summary']['total_students'], 10)

    def test_school_admin_cannot_access_superadmin(self):
        User.objects.create(
            school=self.school1, role='admin',
            full_name='Admin', email='admin@s1.test',
            hashed_password=make_hashed('Password123!'))
        token = get_token(self.client, 'admin@s1.test')
        res = self.client.get(
            '/api/superadmin/overview/',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(res.status_code, 403)

    def test_school_list_excludes_webmasters_kenya(self):
        res = self.client.get(
            '/api/superadmin/schools/',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)
        names = [s['name'] for s in res.json()['schools']]
        self.assertNotIn('Webmasters Kenya', names)
        self.assertIn('School One', names)
        self.assertIn('School Two', names)

    def test_create_school(self):
        res = self.client.post(
            '/api/superadmin/schools/',
            {
                'name': 'New School',
                'county': 'Kisumu',
                'contact_email': 'new@school.ac.ke',
                'admin_name': 'New Admin',
                'admin_email': 'newadmin@school.ac.ke',
                'admin_password': 'NewAdmin123!',
            },
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 201)
        self.assertTrue(
            School.objects.filter(name='New School').exists())
        self.assertTrue(
            User.objects.filter(
                email='newadmin@school.ac.ke',
                role='admin').exists())

    def test_school_detail_returns_metrics(self):
        res = self.client.get(
            f'/api/superadmin/schools/{self.school1.id}/',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn('school', data)
        self.assertIn('trend_7days', data)
        self.assertIn('low_balance_students', data)

    def test_student_list_all_schools(self):
        res = self.client.get(
            '/api/superadmin/students/',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['count'], 10)

    def test_student_list_filter_by_school(self):
        res = self.client.get(
            f'/api/superadmin/students/?school_id={self.school1.id}',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['count'], 5)

    def test_create_staff_account(self):
        res = self.client.post(
            '/api/superadmin/staff/',
            {
                'school_id': self.school1.id,
                'role': 'kitchen',
                'full_name': 'New Kitchen',
                'email': 'newkitchen@s1.test',
                'password': 'Kitchen123!',
            },
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 201)
        self.assertTrue(
            User.objects.filter(
                email='newkitchen@s1.test',
                role='kitchen').exists())

    def test_analytics_returns_balance_distribution(self):
        res = self.client.get(
            '/api/superadmin/analytics/',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn('balance_distribution', data)
        self.assertIn('weekly_collections_per_school', data)

    def test_network_payment_csv(self):
        res = self.client.get(
            '/api/superadmin/reports/payments/',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)
        self.assertIn('text/csv', res['Content-Type'])

    def test_network_summary_report(self):
        res = self.client.get(
            '/api/superadmin/reports/summary/',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn('network_summary', data)
        self.assertEqual(len(data['network_summary']), 2)

    def test_data_isolation_school_admin(self):
        # School 1 admin should NOT see school 2 students
        User.objects.create(
            school=self.school1, role='admin',
            full_name='S1 Admin', email='s1admin@test.com',
            hashed_password=make_hashed('Password123!'))
        token = get_token(self.client, 's1admin@test.com')
        res = self.client.get(
            '/api/payments/balances/',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(res.status_code, 200)
        names = [s['student_name'] for s in res.json()]
        # Should only contain school 1 students
        school2_students = User.objects.filter(
            school=self.school2,
            role='student'
        ).values_list('full_name', flat=True)
        for name in school2_students:
            self.assertNotIn(name, names)
