"""
Phone push notifications: token registration, the three triggers (meal
collected, top-up confirmed/failed, low-balance reminders) and the rules that
keep delivery from ever breaking the request that caused it.
"""
import io
from datetime import date
from unittest import mock

import bcrypt
from django.core.management import call_command
from django.test import TestCase, override_settings

from accounts.views import get_tokens_for_user
from meals.models import (DeviceToken, MealAccount, MenuItem,
                          PaymentTransaction, PushReminderLog, School, User)

GOOD = 'ExponentPushToken[abcdefghijklmnopqrstuv]'
OTHER = 'ExponentPushToken[zzzzzzzzzzzzzzzzzzzzzz]'
STUDENT_TOKEN = 'ExpoPushToken[studentstudentstudent00]'
STRANGER = 'ExponentPushToken[strangerstrangerstran00]'


def make_user(school, role, email, name=None):
    return User.objects.create(
        school=school, role=role, full_name=name or email.split('@')[0],
        email=email,
        hashed_password=bcrypt.hashpw(b'x', bcrypt.gensalt()).decode())


def bearer(user):
    return {'HTTP_AUTHORIZATION': f"Bearer {get_tokens_for_user(user)['access']}"}


class PushBase(TestCase):
    def setUp(self):
        self.school = School.objects.create(name='S', county='N', contact_email='s@t.com')
        self.parent = make_user(self.school, 'parent', 'parent@t.com', 'Pat Parent')
        self.student = make_user(self.school, 'student', 'kid@t.com', 'Kim Kid')
        self.kitchen = make_user(self.school, 'kitchen', 'cook@t.com')
        self.stranger = make_user(self.school, 'parent', 'stranger@t.com')
        self.account = MealAccount.objects.create(student=self.student, balance_cents=50000)
        self.account.guardians.add(self.parent)
        self.item = MenuItem.objects.create(school=self.school, name='Rice', price_cents=3000)
        DeviceToken.objects.create(user=self.parent, token=GOOD)
        DeviceToken.objects.create(user=self.student, token=STUDENT_TOKEN)
        DeviceToken.objects.create(user=self.stranger, token=STRANGER)

    def post(self, url, body, user, method='post'):
        return getattr(self.client, method)(
            url, body, content_type='application/json', **bearer(user))


@override_settings(PUSH_SYNC=True, DARAJA_CALLBACK_TOKEN='test-token')
class TestPushDelivery(PushBase):
    def serve(self):
        with self.captureOnCommitCallbacks(execute=True):
            return self.post('/api/meals/serve/', {
                'student_id': self.student.id, 'item_ids': [self.item.id]}, self.kitchen)

    @mock.patch('meals.push._post_to_expo')
    def test_meal_collected_notifies_parent_and_student_only(self, post):
        post.return_value = [{'status': 'ok'}, {'status': 'ok'}]
        self.assertEqual(self.serve().status_code, 201)
        self.assertEqual(post.call_count, 1)
        messages = post.call_args.args[0]
        self.assertEqual({m['to'] for m in messages}, {GOOD, STUDENT_TOKEN})
        self.assertNotIn(STRANGER, {m['to'] for m in messages})
        first = messages[0]
        self.assertEqual(first['title'], 'Kim Kid collected a meal')
        self.assertIn('Rice', first['body'])
        self.assertIn('KES 30.00 deducted', first['body'])
        self.assertIn('KES 470.00', first['body'])
        self.assertEqual(first['data']['type'], 'meal')
        self.assertEqual(first['data']['meal_account_id'], self.account.id)
        self.assertEqual(first['channelId'], 'default')

    @mock.patch('meals.push._post_to_expo')
    def test_nothing_sent_when_nobody_has_a_registered_phone(self, post):
        DeviceToken.objects.all().delete()
        self.assertEqual(self.serve().status_code, 201)
        post.assert_not_called()

    @mock.patch('meals.push._post_to_expo')
    def test_push_can_be_switched_off(self, post):
        with override_settings(PUSH_ENABLED=False):
            self.assertEqual(self.serve().status_code, 201)
        post.assert_not_called()

    @mock.patch('meals.push._post_to_expo', side_effect=RuntimeError('expo is down'))
    def test_expo_failure_never_breaks_the_meal_serve(self, post):
        res = self.serve()
        self.assertEqual(res.status_code, 201)
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance_cents, 47000)

    @mock.patch('meals.push._post_to_expo')
    def test_rejected_meal_sends_nothing(self, post):
        self.account.balance_cents = 0
        self.account.save()
        res = self.serve()
        self.assertEqual(res.status_code, 402)
        post.assert_not_called()

    @mock.patch('meals.push._post_to_expo')
    def test_unregistered_device_token_is_forgotten(self, post):
        post.return_value = [
            {'status': 'error', 'message': 'gone',
             'details': {'error': 'DeviceNotRegistered'}},
            {'status': 'ok'},
        ]
        self.serve()
        sent_to = [m['to'] for m in post.call_args.args[0]]
        dead = sent_to[0]
        self.assertFalse(DeviceToken.objects.filter(token=dead).exists())
        self.assertTrue(DeviceToken.objects.filter(token=sent_to[1]).exists())

    # ---- M-Pesa callback ----------------------------------------------------
    def callback(self, ref, code):
        stk = {'ResultCode': code, 'ResultDesc': 'x', 'CheckoutRequestID': ref}
        if code == 0:
            tx = PaymentTransaction.objects.get(mpesa_reference=ref)
            stk['CallbackMetadata'] = {'Item': [
                {'Name': 'Amount', 'Value': tx.amount_cents // 100},
                {'Name': 'MpesaReceiptNumber', 'Value': f'R{ref}'}]}
        payload = {'Body': {'stkCallback': stk}}
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post('/api/payments/callback/test-token/', payload,
                                    content_type='application/json')

    @mock.patch('meals.push._post_to_expo')
    def test_confirmed_topup_notifies_the_family(self, post):
        post.return_value = [{'status': 'ok'}, {'status': 'ok'}]
        PaymentTransaction.objects.create(
            meal_account=self.account, amount_cents=50000, mpesa_reference='ws_ok')
        self.assertEqual(self.callback('ws_ok', 0).status_code, 200)
        message = post.call_args.args[0][0]
        self.assertEqual(message['title'], 'Top-up received')
        self.assertIn('KES 500.00 added to Kim Kid', message['body'])
        self.assertIn('New balance: KES 1,000.00', message['body'])
        self.assertEqual(message['data']['status'], 'confirmed')

    @mock.patch('meals.push._post_to_expo')
    def test_failed_topup_notifies_the_family(self, post):
        post.return_value = [{'status': 'ok'}, {'status': 'ok'}]
        PaymentTransaction.objects.create(
            meal_account=self.account, amount_cents=20000, mpesa_reference='ws_fail')
        self.callback('ws_fail', 1032)
        message = post.call_args.args[0][0]
        self.assertEqual(message['title'], 'Top-up not completed')
        self.assertEqual(message['data']['status'], 'failed')
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance_cents, 50000)

    @mock.patch('meals.push._post_to_expo')
    def test_duplicate_callback_does_not_notify_twice(self, post):
        post.return_value = [{'status': 'ok'}, {'status': 'ok'}]
        PaymentTransaction.objects.create(
            meal_account=self.account, amount_cents=50000, mpesa_reference='ws_dup')
        self.callback('ws_dup', 0)
        self.callback('ws_dup', 0)
        self.assertEqual(post.call_count, 1)


class TestPushTokenEndpoint(PushBase):
    URL = '/api/auth/push-token/'

    def test_register_a_token(self):
        new = 'ExponentPushToken[brandnewbrandnewbrandn]'
        res = self.post(self.URL, {'token': new, 'platform': 'android'}, self.parent)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(DeviceToken.objects.filter(token=new, user=self.parent).exists())

    def test_registering_twice_keeps_one_row(self):
        for _ in range(2):
            self.post(self.URL, {'token': GOOD}, self.parent)
        self.assertEqual(DeviceToken.objects.filter(token=GOOD).count(), 1)

    def test_rejects_malformed_tokens(self):
        for token in (None, '', 'not-a-token', 123, ['x'], 'ExponentPushToken[' + 'a' * 300 + ']'):
            res = self.post(self.URL, {'token': token}, self.parent)
            self.assertEqual(res.status_code, 400, repr(token))

    def test_rejects_unknown_platform(self):
        res = self.post(self.URL, {'token': OTHER, 'platform': 'toaster'}, self.parent)
        self.assertEqual(res.status_code, 400)

    def test_requires_login(self):
        res = self.client.post(self.URL, {'token': OTHER}, content_type='application/json')
        self.assertEqual(res.status_code, 401)

    def test_token_moves_to_the_user_who_logs_in_on_that_phone(self):
        res = self.post(self.URL, {'token': GOOD}, self.stranger)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(DeviceToken.objects.get(token=GOOD).user_id, self.stranger.id)

    def test_remove_token_only_removes_your_own(self):
        res = self.post(self.URL, {'token': STRANGER}, self.parent, method='delete')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(DeviceToken.objects.filter(token=STRANGER).exists())
        res = self.post(self.URL, {'token': GOOD}, self.parent, method='delete')
        self.assertEqual(res.status_code, 200)
        self.assertFalse(DeviceToken.objects.filter(token=GOOD).exists())


@override_settings(PUSH_SYNC=True)
class TestPaymentReminders(PushBase):
    def run_command(self, *args, weekday=2):
        """Run the command pretending today is a given weekday (0 = Monday)."""
        out = io.StringIO()
        fake_today = date(2026, 11, 2 + weekday)  # 2 Nov 2026 is a Monday
        with mock.patch(
                'meals.management.commands.send_payment_reminders.date') as d:
            d.today.return_value = fake_today
            call_command('send_payment_reminders', *args, stdout=out)
        return out.getvalue()

    @mock.patch('meals.push._post_to_expo')
    def test_low_balance_family_is_reminded_once_a_day(self, post):
        post.return_value = [{'status': 'ok'}, {'status': 'ok'}]
        self.account.balance_cents = 4000
        self.account.save()
        self.run_command()
        self.assertEqual(post.call_count, 1)
        message = post.call_args.args[0][0]
        self.assertEqual(message['title'], 'Low meal balance')
        self.assertIn('Kim Kid', message['body'])
        self.assertIn('KES 40.00', message['body'])
        self.assertEqual(message['data']['type'], 'reminder')
        self.assertEqual(PushReminderLog.objects.count(), 1)
        self.run_command()  # same day again
        self.assertEqual(post.call_count, 1)

    @mock.patch('meals.push._post_to_expo')
    def test_healthy_balance_is_not_reminded(self, post):
        self.run_command()
        post.assert_not_called()
        self.assertEqual(PushReminderLog.objects.count(), 0)

    @mock.patch('meals.push._post_to_expo')
    def test_weekend_is_skipped_unless_forced(self, post):
        post.return_value = [{'status': 'ok'}, {'status': 'ok'}]
        self.account.balance_cents = 0
        self.account.save()
        self.run_command(weekday=5)
        post.assert_not_called()
        self.run_command('--force', weekday=5)
        self.assertEqual(post.call_count, 1)

    @mock.patch('meals.push._post_to_expo')
    def test_dry_run_sends_nothing_and_logs_nothing(self, post):
        self.account.balance_cents = 0
        self.account.save()
        output = self.run_command('--dry-run')
        post.assert_not_called()
        self.assertIn('Kim Kid', output)
        self.assertEqual(PushReminderLog.objects.count(), 0)

    @mock.patch('meals.push._post_to_expo')
    def test_account_with_no_registered_phone_is_not_logged_as_reminded(self, post):
        DeviceToken.objects.all().delete()
        self.account.balance_cents = 0
        self.account.save()
        self.run_command()
        post.assert_not_called()
        self.assertEqual(PushReminderLog.objects.count(), 0)
