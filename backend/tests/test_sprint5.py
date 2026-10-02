from django.test import TestCase
from meals.models import (School, User, MealAccount,
                           PaymentTransaction, AnomalyFlag,
                           MealDistributionEvent, MenuItem)
from datetime import date
import bcrypt
import json


def make_hashed(p):
    return bcrypt.hashpw(
        p.encode(), bcrypt.gensalt()).decode()


def create_school(name='Test School', email='test@school.com'):
    return School.objects.create(
        name=name, county='Nairobi',
        contact_email=email)


def create_user(school, role, name, email,
                password='Password123!'):
    return User.objects.create(
        school=school, role=role,
        full_name=name, email=email,
        hashed_password=make_hashed(password))


def get_token(client, email, password='Password123!'):
    res = client.post('/api/auth/login/', {
        'email': email, 'password': password
    }, content_type='application/json')
    return res.json()['tokens']['access']


# ════════════════════════════════════════
# AUTH TESTS
# ════════════════════════════════════════

class TestAuthentication(TestCase):
    def setUp(self):
        self.school = create_school('Auth School', 'auth@test.com')

    def test_register_student_creates_meal_account(self):
        res = self.client.post('/api/auth/register/', {
            'full_name': 'Test Student',
            'email': 'reg@test.com',
            'password': 'Password123!',
            'role': 'student',
            'school_id': self.school.id
        }, content_type='application/json')
        self.assertEqual(res.status_code, 201)
        self.assertTrue(
            MealAccount.objects.filter(
                student__email='reg@test.com').exists())

    def test_register_parent_no_meal_account(self):
        res = self.client.post('/api/auth/register/', {
            'full_name': 'Parent User',
            'email': 'parent@test.com',
            'password': 'Password123!',
            'role': 'parent',
            'school_id': self.school.id
        }, content_type='application/json')
        self.assertEqual(res.status_code, 201)
        self.assertFalse(
            MealAccount.objects.filter(
                student__email='parent@test.com').exists())

    def test_duplicate_email_rejected(self):
        create_user(self.school, 'student',
                    'Existing', 'exists@test.com')
        res = self.client.post('/api/auth/register/', {
            'full_name': 'New',
            'email': 'exists@test.com',
            'password': 'Password123!',
            'role': 'student',
            'school_id': self.school.id
        }, content_type='application/json')
        self.assertEqual(res.status_code, 400)

    def test_login_valid_returns_tokens(self):
        create_user(self.school, 'admin',
                    'Admin', 'admin@test.com')
        res = self.client.post('/api/auth/login/', {
            'email': 'admin@test.com',
            'password': 'Password123!'
        }, content_type='application/json')
        self.assertEqual(res.status_code, 200)
        self.assertIn('access', res.json()['tokens'])
        self.assertIn('refresh', res.json()['tokens'])

    def test_login_wrong_password_returns_401(self):
        create_user(self.school, 'admin',
                    'Admin', 'admin2@test.com')
        res = self.client.post('/api/auth/login/', {
            'email': 'admin2@test.com',
            'password': 'WrongPassword!'
        }, content_type='application/json')
        self.assertEqual(res.status_code, 401)

    def test_profile_requires_auth(self):
        res = self.client.get('/api/auth/profile/')
        self.assertEqual(res.status_code, 401)

    def test_profile_returns_data_with_token(self):
        create_user(self.school, 'kitchen',
                    'Kitchen', 'kitchen@test.com')
        token = get_token(self.client, 'kitchen@test.com')
        res = self.client.get(
            '/api/auth/profile/',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['role'], 'kitchen')

    def test_schools_endpoint_public(self):
        res = self.client.get('/api/auth/schools/')
        self.assertEqual(res.status_code, 200)


# ════════════════════════════════════════
# PAYMENT TESTS
# ════════════════════════════════════════

class TestPayments(TestCase):
    def setUp(self):
        self.school = create_school(
            'Pay School', 'pay@test.com')
        self.student = create_user(
            self.school, 'student', 'Student', 'stu@pay.com')
        self.meal_account = MealAccount.objects.create(
            student=self.student, balance_cents=100000)
        self.token = get_token(self.client, 'stu@pay.com')

        self.tx = PaymentTransaction.objects.create(
            meal_account=self.meal_account,
            amount_cents=50000,
            mpesa_reference='TEST_REF_001',
            status='pending'
        )

    def test_confirmed_callback_updates_balance(self):
        payload = {
            "Body": {
                "stkCallback": {
                    "CheckoutRequestID": "TEST_REF_001",
                    "ResultCode": 0,
                    "ResultDesc": "Success",
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": 500},
                            {"Name": "MpesaReceiptNumber",
                             "Value": "QK7TEST"}
                        ]
                    }
                }
            }
        }
        res = self.client.post(
            '/api/payments/callback/',
            json.dumps(payload),
            content_type='application/json')
        self.assertEqual(res.status_code, 200)
        self.tx.refresh_from_db()
        self.meal_account.refresh_from_db()
        self.assertEqual(self.tx.status, 'confirmed')
        self.assertEqual(
            self.meal_account.balance_cents, 150000)

    def test_failed_callback_no_balance_change(self):
        payload = {
            "Body": {
                "stkCallback": {
                    "CheckoutRequestID": "TEST_REF_001",
                    "ResultCode": 1032,
                    "ResultDesc": "Cancelled by user."
                }
            }
        }
        res = self.client.post(
            '/api/payments/callback/',
            json.dumps(payload),
            content_type='application/json')
        self.assertEqual(res.status_code, 200)
        self.tx.refresh_from_db()
        self.meal_account.refresh_from_db()
        self.assertEqual(self.tx.status, 'failed')
        self.assertEqual(
            self.meal_account.balance_cents, 100000)

    def test_balance_endpoint_returns_correct_amount(self):
        res = self.client.get(
            '/api/payments/balance/',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['balance_ksh'], 1000.0)

    def test_payment_history_returns_transactions(self):
        res = self.client.get(
            '/api/payments/history/',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.json()['transactions'], list)

    def test_parent_can_view_balance_and_history(self):
        # A parent has no meal_account of their own — balance/history must
        # resolve to their linked child's account instead of 404ing.
        parent = create_user(self.school, 'parent', 'Parent', 'parent@pay.com')
        self.meal_account.guardians.add(parent)
        token = get_token(self.client, 'parent@pay.com')

        balance_res = self.client.get(
            '/api/payments/balance/',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(balance_res.status_code, 200)
        self.assertEqual(balance_res.json()['student_name'], 'Student')

        history_res = self.client.get(
            '/api/payments/history/',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(history_res.status_code, 200)
        self.assertIsInstance(history_res.json()['transactions'], list)

    def test_minimum_amount_validation(self):
        bursar = create_user(
            self.school, 'bursar', 'Bursar', 'bursar@pay.com')
        token = get_token(self.client, 'bursar@pay.com')
        res = self.client.post(
            '/api/payments/initiate/',
            {'amount_cents': 50,
             'phone_number': '254708374149'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 400)


# ════════════════════════════════════════
# MEAL DISTRIBUTION TESTS
# ════════════════════════════════════════

class TestMealDistribution(TestCase):
    def setUp(self):
        self.school = create_school(
            'Meal School', 'meal@test.com')
        self.student = create_user(
            self.school, 'student',
            'Meal Student', 'mealstu@test.com')
        self.meal_account = MealAccount.objects.create(
            student=self.student, balance_cents=100000)
        self.kitchen = create_user(
            self.school, 'kitchen',
            'Kitchen', 'mealkit@test.com')
        self.token = get_token(self.client, 'mealkit@test.com')
        self.meal_item = MenuItem.objects.create(
            school=self.school, name='Standard Meal', price_cents=5000)

    def test_record_meal_deducts_5000_cents(self):
        res = self.client.post(
            '/api/meals/serve/',
            {'student_id': self.student.id, 'item_ids': [self.meal_item.id]},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 201)
        self.meal_account.refresh_from_db()
        self.assertEqual(self.meal_account.balance_cents, 95000)

    def test_duplicate_meal_returns_409(self):
        MealDistributionEvent.objects.create(
            meal_account=self.meal_account,
            recorded_by=self.kitchen,
            meal_date=date.today(),
            meals_served=1)
        res = self.client.post(
            '/api/meals/serve/',
            {'student_id': self.student.id, 'item_ids': [self.meal_item.id]},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 409)

    def test_insufficient_balance_returns_402(self):
        self.meal_account.balance_cents = 1000
        self.meal_account.save()
        res = self.client.post(
            '/api/meals/serve/',
            {'student_id': self.student.id, 'item_ids': [self.meal_item.id]},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 402)

    def test_student_lookup_returns_eligibility(self):
        res = self.client.get(
            f'/api/meals/lookup/?id={self.student.id}',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)
        data = res.json()['students'][0]
        self.assertTrue(data['eligible'])
        self.assertFalse(data['already_served_today'])

    def test_distribution_log_returns_todays_events(self):
        MealDistributionEvent.objects.create(
            meal_account=self.meal_account,
            recorded_by=self.kitchen,
            meal_date=date.today(),
            meals_served=1)
        admin = create_user(
            self.school, 'admin',
            'Admin', 'mealadmin@test.com')
        token = get_token(self.client, 'mealadmin@test.com')
        res = self.client.get(
            '/api/meals/log/',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(
            res.json()['total_meals_served'], 1)

    def test_non_kitchen_cannot_serve_meal(self):
        parent = create_user(
            self.school, 'parent',
            'Parent', 'mealparent@test.com')
        token = get_token(self.client, 'mealparent@test.com')
        res = self.client.post(
            '/api/meals/serve/',
            {'student_id': self.student.id},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(res.status_code, 403)


# ════════════════════════════════════════
# ANOMALY DETECTION TESTS
# ════════════════════════════════════════

class TestAnomalyDetection(TestCase):
    def setUp(self):
        self.school = create_school(
            'Anomaly School', 'anom@test.com')
        self.bursar = create_user(
            self.school, 'bursar',
            'Bursar', 'anombursar@test.com')
        self.student = create_user(
            self.school, 'student',
            'Student', 'anomstu@test.com')
        self.meal_account = MealAccount.objects.create(
            student=self.student, balance_cents=500000)
        self.token = get_token(
            self.client, 'anombursar@test.com')

        self.tx = PaymentTransaction.objects.create(
            meal_account=self.meal_account,
            amount_cents=500000,
            mpesa_reference='ANOM_TEST_001',
            status='confirmed'
        )
        self.flag = AnomalyFlag.objects.create(
            transaction=self.tx,
            anomaly_score=0.87,
            reviewed=False
        )

    def test_flag_queue_returns_flags(self):
        res = self.client.get(
            '/api/anomalies/flags/',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(res.json()['total'], 1)
        self.assertGreaterEqual(res.json()['pending'], 1)

    def test_filter_pending_flags(self):
        res = self.client.get(
            '/api/anomalies/flags/?reviewed=false',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)
        flags = res.json()['flags']
        self.assertTrue(all(not f['reviewed'] for f in flags))

    def test_review_flag_marks_reviewed(self):
        res = self.client.post(
            f'/api/anomalies/flags/{self.flag.id}/review/',
            {
                'action': 'legitimate',
                'review_notes': 'Verified with parent'
            },
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)
        self.flag.refresh_from_db()
        self.assertTrue(self.flag.reviewed)
        self.assertEqual(
            self.flag.review_notes, 'Verified with parent')

    def test_double_review_returns_409(self):
        self.flag.reviewed = True
        self.flag.save()
        res = self.client.post(
            f'/api/anomalies/flags/{self.flag.id}/review/',
            {'action': 'legitimate', 'review_notes': ''},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 409)

    def test_anomaly_stats_returns_counts(self):
        res = self.client.get(
            '/api/anomalies/stats/',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn('total_flags', data)
        self.assertIn('pending_review', data)
        self.assertIn('high_severity', data)

    def test_non_bursar_cannot_access_flags(self):
        student_token = get_token(
            self.client, 'anomstu@test.com')
        res = self.client.get(
            '/api/anomalies/flags/',
            HTTP_AUTHORIZATION=f'Bearer {student_token}')
        self.assertEqual(res.status_code, 403)


# ════════════════════════════════════════
# REPORT TESTS
# ════════════════════════════════════════

class TestReports(TestCase):
    def setUp(self):
        self.school = create_school(
            'Report School', 'report@test.com')
        self.admin = create_user(
            self.school, 'admin',
            'Admin', 'reportadmin@test.com')
        self.token = get_token(
            self.client, 'reportadmin@test.com')

    def test_payment_csv_returns_200(self):
        res = self.client.get(
            '/api/reports/payments/csv/',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)
        self.assertIn('text/csv', res['Content-Type'])

    def test_meal_csv_returns_200(self):
        res = self.client.get(
            '/api/reports/meals/csv/',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)
        self.assertIn('text/csv', res['Content-Type'])

    def test_anomaly_csv_returns_200(self):
        res = self.client.get(
            '/api/reports/anomalies/csv/',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)
        self.assertIn('text/csv', res['Content-Type'])

    def test_term_summary_returns_stats(self):
        res = self.client.get(
            '/api/reports/summary/',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn('students', data)
        self.assertIn('payments', data)
        self.assertIn('meals', data)
        self.assertIn('anomalies', data)

    def test_non_admin_cannot_access_reports(self):
        student = create_user(
            self.school, 'student',
            'Stu', 'repstu@test.com')
        MealAccount.objects.create(
            student=student, balance_cents=10000)
        token = get_token(self.client, 'repstu@test.com')
        res = self.client.get(
            '/api/reports/summary/',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(res.status_code, 403)
