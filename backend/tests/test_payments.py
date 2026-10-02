from django.test import TestCase
from meals.models import School, User, MealAccount, PaymentTransaction
from unittest.mock import patch, MagicMock
import bcrypt
import json


def make_hashed(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


class TestPaymentInitiate(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name='Test School', county='Nairobi',
            contact_email='pay@test.com')
        self.student = User.objects.create(
            school=self.school, role='student',
            full_name='Test Student', email='student@pay.com',
            hashed_password=make_hashed('Password123!'))
        self.meal_account = MealAccount.objects.create(
            student=self.student, balance_cents=50000)

        # Login to get token
        login = self.client.post('/api/auth/login/', {
            'email': 'student@pay.com',
            'password': 'Password123!'
        }, content_type='application/json')
        self.token = login.json()['tokens']['access']

    @patch('payments.views.MPesaService')
    def test_initiate_payment_creates_pending_transaction(self, MockMpesa):
        mock_instance = MockMpesa.return_value
        mock_instance.stk_push.return_value = {
            'CheckoutRequestID': 'ws_CO_TEST123',
            'ResponseCode': '0',
            'ResponseDescription': 'Success'
        }

        response = self.client.post(
            '/api/payments/initiate/',
            {'amount_cents': 50000, 'phone_number': '254708374149'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('checkout_request_id', response.json())
        self.assertTrue(
            PaymentTransaction.objects.filter(
                status='pending',
                meal_account=self.meal_account).exists())

    def test_initiate_payment_requires_auth(self):
        response = self.client.post(
            '/api/payments/initiate/',
            {'amount_cents': 50000, 'phone_number': '254708374149'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 401)

    def test_minimum_amount_validation(self):
        response = self.client.post(
            '/api/payments/initiate/',
            {'amount_cents': 50, 'phone_number': '254708374149'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        self.assertEqual(response.status_code, 400)


class TestMpesaCallback(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name='CB School', county='Nairobi',
            contact_email='cb@test.com')
        self.student = User.objects.create(
            school=self.school, role='student',
            full_name='CB Student', email='cb@test.com',
            hashed_password=make_hashed('Password123!'))
        self.meal_account = MealAccount.objects.create(
            student=self.student, balance_cents=50000)
        self.tx = PaymentTransaction.objects.create(
            meal_account=self.meal_account,
            amount_cents=50000,
            mpesa_reference='ws_CO_TEST456',
            status='pending'
        )

    def test_confirmed_callback_updates_balance(self):
        payload = {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "test",
                    "CheckoutRequestID": "ws_CO_TEST456",
                    "ResultCode": 0,
                    "ResultDesc": "The service request is processed successfully.",
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": 500},
                            {"Name": "MpesaReceiptNumber", "Value": "QK7X3RY8"},
                            {"Name": "PhoneNumber", "Value": 254708374149}
                        ]
                    }
                }
            }
        }
        response = self.client.post(
            '/api/payments/callback/',
            json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.tx.refresh_from_db()
        self.meal_account.refresh_from_db()
        self.assertEqual(self.tx.status, 'confirmed')
        self.assertEqual(self.meal_account.balance_cents, 100000)

    def test_failed_callback_does_not_update_balance(self):
        payload = {
            "Body": {
                "stkCallback": {
                    "CheckoutRequestID": "ws_CO_TEST456",
                    "ResultCode": 1032,
                    "ResultDesc": "Request cancelled by user."
                }
            }
        }
        response = self.client.post(
            '/api/payments/callback/',
            json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.tx.refresh_from_db()
        self.meal_account.refresh_from_db()
        self.assertEqual(self.tx.status, 'failed')
        self.assertEqual(self.meal_account.balance_cents, 50000)


class TestPaymentStatus(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name='Status School', county='Nairobi',
            contact_email='status@test.com')
        self.student = User.objects.create(
            school=self.school, role='student',
            full_name='Status Student', email='status@test.com',
            hashed_password=make_hashed('Password123!'))
        self.meal_account = MealAccount.objects.create(
            student=self.student, balance_cents=50000)
        self.tx = PaymentTransaction.objects.create(
            meal_account=self.meal_account,
            amount_cents=50000,
            mpesa_reference='ws_CO_STATUS',
            status='pending'
        )
        login = self.client.post('/api/auth/login/', {
            'email': 'status@test.com',
            'password': 'Password123!'
        }, content_type='application/json')
        self.token = login.json()['tokens']['access']

    def test_status_returns_pending(self):
        response = self.client.get(
            f'/api/payments/status/{self.tx.id}/',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'pending')

    def test_balance_returned_on_confirmed(self):
        self.tx.status = 'confirmed'
        self.tx.save()
        response = self.client.get(
            f'/api/payments/status/{self.tx.id}/',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        self.assertEqual(response.json()['new_balance_ksh'], 500.0)
