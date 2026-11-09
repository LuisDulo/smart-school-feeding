"""
Daraja only charges whole shillings, and stk_push rounds the amount down.
A top-up of 199 cents used to charge the payer KES 1 but credit KES 1.99,
so part-shilling amounts must be refused before any money moves.
"""
from unittest.mock import patch

import bcrypt
from django.test import TestCase

from meals.models import MealAccount, PaymentTransaction, School, User


class TestTopUpAmount(TestCase):
    def setUp(self):
        school = School.objects.create(
            name='Amount School', county='Nairobi', contact_email='amt@test.com')
        student = User.objects.create(
            school=school, role='student', full_name='Amount Student',
            email='amt@test.com',
            hashed_password=bcrypt.hashpw(b'Password123!', bcrypt.gensalt()).decode())
        MealAccount.objects.create(student=student, balance_cents=0)
        login = self.client.post('/api/auth/login/', {
            'email': 'amt@test.com', 'password': 'Password123!'},
            content_type='application/json')
        self.auth = f"Bearer {login.json()['tokens']['access']}"

    def initiate(self, amount_cents):
        return self.client.post(
            '/api/payments/initiate/',
            {'amount_cents': amount_cents, 'phone_number': '254708374149'},
            content_type='application/json', HTTP_AUTHORIZATION=self.auth)

    @patch('payments.views.MPesaService')
    def test_part_shilling_amount_is_refused(self, mpesa):
        response = self.initiate(199)
        self.assertEqual(response.status_code, 400)
        mpesa.return_value.stk_push.assert_not_called()
        self.assertFalse(PaymentTransaction.objects.exists())

    @patch('payments.views.MPesaService')
    def test_whole_shilling_amount_is_accepted(self, mpesa):
        mpesa.return_value.stk_push.return_value = {'CheckoutRequestID': 'ws_CO_AMT'}
        self.assertEqual(self.initiate(20000).status_code, 200)

    @patch('payments.views.MPesaService')
    def test_no_checkout_id_from_daraja_fails_the_transaction(self, mpesa):
        # A pending row with an empty reference could later be matched by a
        # callback that sends an empty CheckoutRequestID.
        mpesa.return_value.stk_push.return_value = {'errorMessage': 'Bad Request'}
        response = self.initiate(20000)
        self.assertEqual(response.status_code, 502)
        self.assertFalse(PaymentTransaction.objects.filter(status='pending').exists())
