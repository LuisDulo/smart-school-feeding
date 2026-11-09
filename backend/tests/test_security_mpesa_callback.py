"""
The M-Pesa callback is the only endpoint that adds money to a meal account,
and Daraja calls it without any credentials. Before this fix, anyone who
knew a pending CheckoutRequestID (the initiate endpoint hands it to the
client) could POST a made-up "ResultCode 0" and have the balance credited
without paying.

These tests pin down the fix:
- the callback only answers at a URL that carries a secret token,
- a success is credited only when its amount matches what was charged and it
  carries an M-Pesa receipt that has not been used before,
- phone numbers in the payload are not written to the logs.
"""
import json

import bcrypt
from django.test import TestCase, override_settings

from meals.models import MealAccount, PaymentTransaction, School, User

TOKEN = 'cb-test-token-0123456789abcdef0123456789'


def callback(checkout_id, result_code=0, amount=500, receipt='QK7X3RY8',
             phone=254708374149):
    body = {
        'MerchantRequestID': 'test',
        'CheckoutRequestID': checkout_id,
        'ResultCode': result_code,
        'ResultDesc': 'The service request is processed successfully.',
    }
    if result_code == 0:
        items = [{'Name': 'Amount', 'Value': amount},
                 {'Name': 'PhoneNumber', 'Value': phone}]
        if receipt is not None:
            items.append({'Name': 'MpesaReceiptNumber', 'Value': receipt})
        body['CallbackMetadata'] = {'Item': items}
    return json.dumps({'Body': {'stkCallback': body}})


@override_settings(DARAJA_CALLBACK_TOKEN=TOKEN)
class TestForgedCallbacks(TestCase):
    def setUp(self):
        school = School.objects.create(
            name='Callback School', county='Nairobi',
            contact_email='cbsec@test.com')
        student = User.objects.create(
            school=school, role='student', full_name='Callback Student',
            email='cbsec@test.com',
            hashed_password=bcrypt.hashpw(b'x', bcrypt.gensalt()).decode())
        self.account = MealAccount.objects.create(
            student=student, balance_cents=50000)
        self.tx = PaymentTransaction.objects.create(
            meal_account=self.account, amount_cents=50000,
            mpesa_reference='ws_CO_SEC1', status='pending')

    def post(self, path, payload):
        return self.client.post(path, payload, content_type='application/json')

    def assert_not_credited(self):
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance_cents, 50000)

    def test_old_public_callback_url_no_longer_credits(self):
        response = self.post('/api/payments/callback/', callback('ws_CO_SEC1'))
        self.assertEqual(response.status_code, 404)
        self.assert_not_credited()

    def test_wrong_token_is_refused(self):
        response = self.post('/api/payments/callback/not-the-token/',
                             callback('ws_CO_SEC1'))
        self.assertEqual(response.status_code, 404)
        self.assert_not_credited()

    @override_settings(DARAJA_CALLBACK_TOKEN='')
    def test_no_token_configured_refuses_every_callback(self):
        response = self.post('/api/payments/callback//', callback('ws_CO_SEC1'))
        self.assertEqual(response.status_code, 404)
        self.assert_not_credited()

    def test_amount_that_does_not_match_the_charge_is_not_credited(self):
        self.post(f'/api/payments/callback/{TOKEN}/',
                  callback('ws_CO_SEC1', amount=1))
        self.assert_not_credited()
        self.tx.refresh_from_db()
        self.assertEqual(self.tx.status, 'failed')

    def test_success_without_a_receipt_is_not_credited(self):
        self.post(f'/api/payments/callback/{TOKEN}/',
                  callback('ws_CO_SEC1', receipt=None))
        self.assert_not_credited()

    def test_a_receipt_can_only_be_credited_once(self):
        PaymentTransaction.objects.create(
            meal_account=self.account, amount_cents=50000,
            mpesa_reference='ws_CO_OLD', mpesa_receipt='QK7X3RY8',
            status='confirmed')
        self.post(f'/api/payments/callback/{TOKEN}/',
                  callback('ws_CO_SEC1', receipt='QK7X3RY8'))
        self.assert_not_credited()

    def test_genuine_callback_is_credited_and_keeps_the_receipt(self):
        response = self.post(f'/api/payments/callback/{TOKEN}/',
                             callback('ws_CO_SEC1'))
        self.assertEqual(response.status_code, 200)
        self.account.refresh_from_db()
        self.tx.refresh_from_db()
        self.assertEqual(self.account.balance_cents, 100000)
        self.assertEqual(self.tx.status, 'confirmed')
        self.assertEqual(self.tx.mpesa_receipt, 'QK7X3RY8')

    def test_phone_number_is_not_logged(self):
        with self.assertLogs('payments', level='INFO') as logs:
            self.post(f'/api/payments/callback/{TOKEN}/',
                      callback('ws_CO_SEC1'))
        self.assertNotIn('254708374149', '\n'.join(logs.output))
