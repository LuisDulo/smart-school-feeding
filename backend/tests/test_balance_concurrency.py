"""
Serving a meal, confirming a top-up and approving credit all change a meal
account. They used to read the account, change it in Python and save the
whole row without a lock, so two of them running at once could overwrite
each other: a top-up confirmed while a meal was being served disappeared,
two quick scans of one card both got past the daily limit, and one credit
request approved twice raised the limit twice.

Each test pauses the first request at the moment it is about to write
(using a pre_save signal), runs the second request against the database in
another thread, then lets the first one finish. With the row locks in place
the second request waits for the first, so the result is always correct.
"""
import json
import threading
import time

import bcrypt
from django.db import connection
from django.db.models.signals import pre_save
from django.test import Client, TransactionTestCase, override_settings

from meals.models import (CreditRequest, MealAccount, MealDistributionEvent,
                          MenuItem, PaymentTransaction, School, User)

TOKEN = 'race-test-token-0123456789abcdef01234567'
PASSWORD = 'Password123!'
WAIT = 5  # seconds; only reached if something is broken


def make_user(school, role, name, email):
    return User.objects.create(
        school=school, role=role, full_name=name, email=email,
        hashed_password=bcrypt.hashpw(PASSWORD.encode(),
                                      bcrypt.gensalt()).decode())


def login(email):
    res = Client().post('/api/auth/login/',
                        {'email': email, 'password': PASSWORD},
                        content_type='application/json')
    return res.json()['tokens']['access']


def success_callback(checkout_id, amount_ksh, receipt):
    return json.dumps({'Body': {'stkCallback': {
        'MerchantRequestID': 'race',
        'CheckoutRequestID': checkout_id,
        'ResultCode': 0,
        'ResultDesc': 'The service request is processed successfully.',
        'CallbackMetadata': {'Item': [
            {'Name': 'Amount', 'Value': amount_ksh},
            {'Name': 'MpesaReceiptNumber', 'Value': receipt},
        ]},
    }}})


class PauseFirstSave:
    """Hold the first save of `model` until release() is called."""

    def __init__(self, model):
        self.model = model
        self.reached = threading.Event()
        self.go = threading.Event()
        self.used = False

    def handler(self, sender, **kwargs):
        if self.used:
            return
        self.used = True
        self.reached.set()
        self.go.wait(WAIT)

    def __enter__(self):
        pre_save.connect(self.handler, sender=self.model,
                         dispatch_uid=f'pause-{id(self)}')
        return self

    def __exit__(self, *exc):
        self.go.set()
        pre_save.disconnect(sender=self.model,
                            dispatch_uid=f'pause-{id(self)}')


def run_in_thread(fn, results, key):
    def target():
        try:
            results[key] = fn()
        finally:
            connection.close()
    thread = threading.Thread(target=target)
    thread.start()
    return thread


@override_settings(DARAJA_CALLBACK_TOKEN=TOKEN, PUSH_ENABLED=False)
class TestBalanceConcurrency(TransactionTestCase):
    def setUp(self):
        self.school = School.objects.create(
            name='Race School', county='Nairobi',
            contact_email='race@test.com')
        self.kitchen = make_user(self.school, 'kitchen', 'Race Cook',
                                 'cook@race.test')
        self.admin = make_user(self.school, 'admin', 'Race Admin',
                               'admin@race.test')
        self.student = make_user(self.school, 'student', 'Race Student',
                                 'student@race.test')
        self.account = MealAccount.objects.create(
            student=self.student, balance_cents=50000)
        self.item = MenuItem.objects.create(
            school=self.school, name='Githeri', price_cents=8000)

    def serve(self, token):
        return Client().post(
            '/api/meals/serve/',
            {'student_id': self.student.id, 'item_ids': [self.item.id]},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}').status_code

    def test_top_up_during_a_serve_is_not_lost(self):
        PaymentTransaction.objects.create(
            meal_account=self.account, amount_cents=50000,
            mpesa_reference='ws_CO_RACE1', status='pending')
        token = login('cook@race.test')
        results = {}

        with PauseFirstSave(MealDistributionEvent) as pause:
            serving = run_in_thread(lambda: self.serve(token), results, 'serve')
            self.assertTrue(pause.reached.wait(WAIT))
            paying = run_in_thread(
                lambda: Client().post(
                    f'/api/payments/callback/{TOKEN}/',
                    success_callback('ws_CO_RACE1', 500, 'RACE1RCPT'),
                    content_type='application/json').status_code,
                results, 'callback')
            # Give the callback time to reach the database before the
            # serve continues. With the lock it has to wait for the serve.
            time.sleep(0.5)
            pause.go.set()
            serving.join(WAIT)
            paying.join(WAIT)

        self.assertEqual(results, {'serve': 201, 'callback': 200})
        self.account.refresh_from_db()
        # 500 start + 500 top-up - 80 meal
        self.assertEqual(self.account.balance_cents, 50000 + 50000 - 8000)

    @override_settings(MAX_MEALS_PER_STUDENT_PER_DAY=1)
    def test_two_scans_at_once_cannot_pass_the_daily_limit(self):
        token = login('cook@race.test')
        results = {}

        with PauseFirstSave(MealDistributionEvent) as pause:
            first = run_in_thread(lambda: self.serve(token), results, 'first')
            self.assertTrue(pause.reached.wait(WAIT))
            second = run_in_thread(lambda: self.serve(token), results, 'second')
            time.sleep(0.5)
            pause.go.set()
            first.join(WAIT)
            second.join(WAIT)

        self.assertEqual(results, {'first': 201, 'second': 409})
        self.assertEqual(MealDistributionEvent.objects.filter(
            meal_account=self.account).count(), 1)
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance_cents, 50000 - 8000)

    def test_one_credit_request_cannot_be_approved_twice(self):
        request = CreditRequest.objects.create(
            meal_account=self.account, requested_by=self.student,
            requested_amount_cents=20000, reason='Fees delayed')
        token = login('admin@race.test')
        results = {}

        def approve():
            return Client().post(
                f'/api/payments/credit-requests/{request.id}/review/',
                {'action': 'approved', 'review_notes': ''},
                content_type='application/json',
                HTTP_AUTHORIZATION=f'Bearer {token}').status_code

        with PauseFirstSave(CreditRequest) as pause:
            first = run_in_thread(approve, results, 'first')
            self.assertTrue(pause.reached.wait(WAIT))
            second = run_in_thread(approve, results, 'second')
            time.sleep(0.5)
            pause.go.set()
            first.join(WAIT)
            second.join(WAIT)

        self.assertEqual(results, {'first': 200, 'second': 409})
        self.account.refresh_from_db()
        self.assertEqual(self.account.credit_limit_cents, 20000)
