"""
Meal-serving anomaly detection: features, rules, blocked-attempt tracking,
the review API, and the scan / demo-generator commands.
"""
import io
from datetime import date, datetime, time, timedelta
from unittest import mock

import bcrypt
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.views import get_tokens_for_user
from anomalies import meal_detection
from meals.models import (BlockedServeAttempt, MealAccount, MealAnomalyFlag,
                          MealDistributionEvent, MenuItem, PaymentTransaction,
                          School, User)


def make_user(school, role, email, name=None):
    return User.objects.create(
        school=school, role=role, full_name=name or email.split('@')[0],
        email=email,
        hashed_password=bcrypt.hashpw(b'x', bcrypt.gensalt()).decode())


def bearer(user):
    return {'HTTP_AUTHORIZATION': f"Bearer {get_tokens_for_user(user)['access']}"}


def aware(day, hour, minute=0):
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


def last_weekday(weekday):
    """Most recent date (before today) falling on the given weekday (0 = Mon)."""
    d = date.today() - timedelta(days=1)
    while d.weekday() != weekday:
        d -= timedelta(days=1)
    return d


class MealAnomalyBase(TestCase):
    def setUp(self):
        self.school = School.objects.create(name='A', county='N', contact_email='a@t.com')
        self.other = School.objects.create(name='B', county='N', contact_email='b@t.com')
        self.admin = make_user(self.school, 'admin', 'admin@t.com')
        self.kitchen = make_user(self.school, 'kitchen', 'cook@t.com', 'Cook Carol')
        self.parent = make_user(self.school, 'parent', 'parent@t.com')
        self.other_admin = make_user(self.other, 'admin', 'oadmin@t.com')
        self.students = []
        self.accounts = []
        for i in range(14):
            student = make_user(self.school, 'student', f'kid{i}@t.com', f'Kid {i}')
            self.students.append(student)
            self.accounts.append(MealAccount.objects.create(student=student, balance_cents=100000))
        self.account = self.accounts[0]
        self.item = MenuItem.objects.create(school=self.school, name='Rice', price_cents=5000)
        self.weekday = last_weekday(1)  # a Tuesday

    def make_event(self, account=None, amount=5000, day=None, hour=8, minute=0, staff=None):
        event = MealDistributionEvent.objects.create(
            meal_account=account or self.account, recorded_by=staff or self.kitchen,
            meal_date=day or self.weekday, meals_served=1, amount_cents=amount)
        MealDistributionEvent.objects.filter(pk=event.pk).update(
            created_at=aware(day or self.weekday, hour, minute))
        event.refresh_from_db()
        return event

    def get(self, url, user):
        return self.client.get(url, **bearer(user))

    def post(self, url, user, body=None):
        return self.client.post(url, body or {}, content_type='application/json', **bearer(user))


class TestFeaturesAndRules(MealAnomalyBase):
    def test_model_files_load(self):
        model, scaler = meal_detection.load_model()
        self.assertIsNotNone(model)
        self.assertIsNotNone(scaler)

    def test_live_and_batch_features_agree(self):
        events = [self.make_event(amount=a, hour=h, day=self.weekday - timedelta(days=d))
                  for a, h, d in [(5000, 8, 3), (6000, 12, 2), (5500, 8, 1), (9000, 13, 0)]]
        events.append(self.make_event(amount=4000, hour=13))  # 2nd meal that day
        batch = meal_detection.build_feature_frame().set_index('event_id')
        for event in events:
            live = meal_detection.features_for_event(event).iloc[0]
            for name in meal_detection.FEATURES:
                self.assertAlmostEqual(
                    float(live[name]), float(batch.loc[event.id, name]), places=3,
                    msg=f'{name} differs for event {event.id}')

    def test_ordinary_meal_is_not_flagged(self):
        event = self.make_event(amount=5000, hour=8)
        self.assertFalse(meal_detection.evaluate_event(event)['flag'])
        self.assertIsNone(meal_detection.flag_meal_event(event))

    def test_meal_outside_serving_hours_is_flagged_with_a_reason(self):
        event = self.make_event(hour=2, minute=40)
        result = meal_detection.evaluate_event(event)
        self.assertTrue(result['flag'])
        self.assertIn('02:40', result['reasons'][0])
        self.assertIn('outside school serving hours', result['reasons'][0])
        self.assertGreaterEqual(result['score'], 0.8)

    def test_evening_meal_is_flagged(self):
        self.assertTrue(meal_detection.evaluate_event(self.make_event(hour=17))['flag'])
        self.assertFalse(meal_detection.evaluate_event(self.make_event(hour=16, minute=59, account=self.accounts[1]))['flag'])

    def test_weekend_meal_is_flagged(self):
        saturday = last_weekday(5)
        result = meal_detection.evaluate_event(self.make_event(day=saturday, hour=10))
        self.assertTrue(result['flag'])
        self.assertIn('Saturday', result['reasons'][0])

    def test_meal_far_above_the_students_usual_cost_is_flagged(self):
        for d in range(1, 5):
            self.make_event(amount=5000, day=self.weekday - timedelta(days=d))
        big = self.make_event(amount=30000)
        result = meal_detection.evaluate_event(big)
        self.assertTrue(result['flag'])
        self.assertTrue(any('6.0x' in r and 'usual' in r for r in result['reasons']), result['reasons'])

    def test_cost_rule_needs_history_and_a_minimum_amount(self):
        # First ever meal: no "usual" to compare with, so the cost rule stays quiet.
        first = self.make_event(account=self.accounts[2], amount=30000)
        self.assertFalse(any('usual' in r and 'x this' in r
                             for r in meal_detection.evaluate_event(first)['reasons']))
        # 3x a tiny usual but under KES 150: not flagged by the rule.
        acct = self.accounts[3]
        for d in range(1, 4):
            self.make_event(account=acct, amount=2000, day=self.weekday - timedelta(days=d))
        small = self.make_event(account=acct, amount=7000)
        self.assertFalse(any('x this' in r for r in meal_detection.evaluate_event(small)['reasons']))

    def test_flag_is_stored_once_with_school_account_and_staff(self):
        event = self.make_event(hour=3)
        flag = meal_detection.flag_meal_event(event)
        again = meal_detection.flag_meal_event(event)
        self.assertEqual(flag.id, again.id)
        self.assertEqual(MealAnomalyFlag.objects.count(), 1)
        self.assertEqual((flag.school_id, flag.meal_account_id, flag.recorded_by_id, flag.kind),
                         (self.school.id, self.account.id, self.kitchen.id, 'pattern'))


@override_settings(PUSH_ENABLED=False)
class TestLiveServing(MealAnomalyBase):
    def serve(self, student=None, user=None):
        return self.post('/api/meals/serve/', user or self.kitchen,
                         {'student_id': (student or self.students[0]).id,
                          'item_ids': [self.item.id]})

    @mock.patch('anomalies.meal_detection.flag_meal_event')
    def test_every_served_meal_is_scored(self, scorer):
        self.assertEqual(self.serve().status_code, 201)
        scorer.assert_called_once()
        self.assertEqual(scorer.call_args.args[0].meal_account_id, self.account.id)

    @mock.patch('anomalies.meal_detection.flag_meal_event', side_effect=RuntimeError('boom'))
    def test_scoring_failure_never_breaks_serving(self, scorer):
        self.assertEqual(self.serve().status_code, 201)
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance_cents, 95000)

    def test_blocked_attempts_are_logged_and_repeats_are_flagged(self):
        self.assertEqual(self.serve().status_code, 201)
        self.assertEqual(self.serve().status_code, 201)
        self.assertEqual(self.serve().status_code, 409)           # 1st refusal: logged only
        self.assertEqual(BlockedServeAttempt.objects.count(), 1)
        self.assertFalse(MealAnomalyFlag.objects.filter(kind='repeat_attempts').exists())
        self.assertEqual(self.serve().status_code, 409)           # 2nd refusal: flagged
        flag = MealAnomalyFlag.objects.get(kind='repeat_attempts')
        self.assertEqual(flag.meal_account_id, self.account.id)
        self.assertIn('Kid 0', flag.reasons[0])
        self.assertIn('2 times', flag.reasons[0])
        self.assertEqual(self.serve().status_code, 409)           # 3rd: same flag, updated
        self.assertEqual(MealAnomalyFlag.objects.filter(kind='repeat_attempts').count(), 1)
        flag.refresh_from_db()
        self.assertIn('3 times', flag.reasons[0])
        self.assertGreater(flag.anomaly_score, 0.75)

    def test_a_staff_member_blocked_repeatedly_is_flagged(self):
        for student in self.students[:5]:
            self.serve(student)
            self.serve(student)
            self.assertEqual(self.serve(student).status_code, 409)  # one refusal each
        flag = MealAnomalyFlag.objects.get(kind='staff_attempts')
        self.assertEqual(flag.recorded_by_id, self.kitchen.id)
        self.assertIn('Cook Carol', flag.reasons[0])
        self.assertIsNone(flag.meal_account_id)
        self.assertFalse(MealAnomalyFlag.objects.filter(kind='repeat_attempts').exists())

    def test_a_logging_failure_still_returns_the_refusal(self):
        self.serve()
        self.serve()
        with mock.patch('anomalies.meal_detection.record_blocked_attempt',
                        side_effect=RuntimeError('db down')):
            self.assertEqual(self.serve().status_code, 409)


class TestMealFlagApi(MealAnomalyBase):
    def flag_for(self, account, school=None, hour=3):
        return meal_detection.flag_meal_event(
            self.make_event(account=account, hour=hour))

    def test_list_shows_only_own_school_with_summary(self):
        mine = self.flag_for(self.accounts[0])
        theirs_student = make_user(self.other, 'student', 'theirs@t.com', 'Theirs')
        theirs_account = MealAnomalyFlag.objects.create(
            school=self.other, meal_account=MealAccount.objects.create(student=theirs_student),
            kind='repeat_attempts', flag_date=date.today(), anomaly_score=0.9, reasons=['x'])
        res = self.get('/api/anomalies/meal-flags/', self.admin)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual([f['id'] for f in body['flags']], [mine.id])
        self.assertEqual((body['total'], body['pending'], body['high_severity']), (1, 1, 1))
        flag = body['flags'][0]
        self.assertEqual(flag['student_name'], 'Kid 0')
        self.assertEqual(flag['staff_name'], 'Cook Carol')
        self.assertEqual(flag['severity'], 'HIGH')
        self.assertEqual(flag['meal']['amount_ksh'], 50.0)
        self.assertEqual(flag['kind'], 'pattern')
        self.assertTrue(flag['reasons'])
        self.assertNotEqual(theirs_account.school_id, self.school.id)

    def test_reviewed_filter(self):
        a = self.flag_for(self.accounts[0])
        b = self.flag_for(self.accounts[1])
        MealAnomalyFlag.objects.filter(pk=b.pk).update(reviewed=True)
        ids = lambda q: {f['id'] for f in self.get(f'/api/anomalies/meal-flags/{q}', self.admin).json()['flags']}  # noqa: E731
        self.assertEqual(ids('?reviewed=false'), {a.id})
        self.assertEqual(ids('?reviewed=true'), {b.id})
        self.assertEqual(ids(''), {a.id, b.id})

    def test_only_admin_or_bursar_can_use_it(self):
        for user in (self.parent, self.kitchen):
            self.assertEqual(self.get('/api/anomalies/meal-flags/', user).status_code, 403)
        self.assertEqual(self.client.get('/api/anomalies/meal-flags/').status_code, 401)

    def test_review_marks_the_flag_and_cannot_be_repeated(self):
        flag = self.flag_for(self.accounts[0])
        url = f'/api/anomalies/meal-flags/{flag.id}/review/'
        res = self.post(url, self.admin, {'action': 'confirmed_irregular', 'review_notes': 'checked CCTV'})
        self.assertEqual(res.status_code, 200)
        flag.refresh_from_db()
        self.assertTrue(flag.reviewed)
        self.assertEqual((flag.reviewed_by_id, flag.review_notes), (self.admin.id, 'checked CCTV'))
        self.assertEqual(self.post(url, self.admin, {'action': 'legitimate'}).status_code, 409)

    def test_review_validates_the_action(self):
        flag = self.flag_for(self.accounts[0])
        res = self.post(f'/api/anomalies/meal-flags/{flag.id}/review/', self.admin, {'action': 'shrug'})
        self.assertEqual(res.status_code, 400)

    def test_cannot_review_another_schools_flag_or_as_a_parent(self):
        flag = self.flag_for(self.accounts[0])
        url = f'/api/anomalies/meal-flags/{flag.id}/review/'
        self.assertEqual(self.post(url, self.other_admin, {'action': 'legitimate'}).status_code, 404)
        self.assertEqual(self.post(url, self.parent, {'action': 'legitimate'}).status_code, 403)
        flag.refresh_from_db()
        self.assertFalse(flag.reviewed)

    def test_run_detection_flags_recent_unusual_meals(self):
        self.make_event(hour=2, day=date.today())
        self.make_event(account=self.accounts[1], hour=8, day=date.today())
        res = self.post('/api/anomalies/meal-flags/run/', self.admin, {'days': 7})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['meals_scored'], 2)
        self.assertEqual(res.json()['new_flags_created'], 1)
        self.assertEqual(self.post('/api/anomalies/meal-flags/run/', self.admin).json()['new_flags_created'], 0)

    def test_run_detection_validates_days_and_permissions(self):
        for days in (0, 91, 'abc', None):
            body = {'days': days} if days is not None else {'days': None}
            self.assertEqual(self.post('/api/anomalies/meal-flags/run/', self.admin, body).status_code, 400, days)
        self.assertEqual(self.post('/api/anomalies/meal-flags/run/', self.parent).status_code, 403)


class TestCommands(MealAnomalyBase):
    def run_cmd(self, name, *args):
        out = io.StringIO()
        call_command(name, *args, stdout=out)
        return out.getvalue()

    def test_scan_flags_unusual_meals_once(self):
        self.make_event(hour=2, day=date.today())
        self.assertIn('flagged 1', self.run_cmd('scan_meal_anomalies', '--days', '7', '--dry-run').replace('would flag', 'flagged'))
        self.assertEqual(MealAnomalyFlag.objects.count(), 0)          # dry run saves nothing
        self.assertIn('flagged 1', self.run_cmd('scan_meal_anomalies', '--days', '7'))
        self.assertEqual(MealAnomalyFlag.objects.count(), 1)
        self.assertIn('flagged 0', self.run_cmd('scan_meal_anomalies', '--days', '7'))  # idempotent

    def test_scan_ignores_meals_older_than_the_window(self):
        self.make_event(hour=2, day=date.today() - timedelta(days=20))
        self.run_cmd('scan_meal_anomalies', '--days', '5')
        self.assertEqual(MealAnomalyFlag.objects.count(), 0)

    def test_scan_can_be_limited_to_one_school(self):
        self.make_event(hour=2, day=date.today())
        self.run_cmd('scan_meal_anomalies', '--days', '7', '--school', str(self.other.id))
        self.assertEqual(MealAnomalyFlag.objects.count(), 0)

    def test_simulate_creates_flags_across_payments_and_meals_and_cleans_up(self):
        # A real school has meal history; the "costly meal" case relies on it.
        for account in self.accounts:
            for d in range(1, 4):
                self.make_event(account=account, amount=5000,
                                day=self.weekday - timedelta(days=d))
        history = MealDistributionEvent.objects.count()
        output = self.run_cmd('simulate_anomalies', '--school', str(self.school.id))
        self.assertIn('FLAGGED', output)
        self.assertTrue(PaymentTransaction.objects.filter(mpesa_reference__startswith='SIMULATED-').exists())
        kinds = set(MealAnomalyFlag.objects.values_list('kind', flat=True))
        self.assertEqual(kinds, {'pattern', 'repeat_attempts', 'staff_attempts'})
        self.assertEqual(MealAnomalyFlag.objects.filter(kind='pattern').count(), 3)
        self.assertTrue(all(MealAnomalyFlag.objects.values_list('is_demo', flat=True)))
        balances = list(MealAccount.objects.order_by('id').values_list('balance_cents', flat=True))
        self.assertEqual(set(balances), {100000})                     # no balance is touched

        self.run_cmd('simulate_anomalies', '--school', str(self.school.id))   # re-run replaces
        self.assertEqual(MealAnomalyFlag.objects.filter(kind='pattern').count(), 3)

        self.run_cmd('simulate_anomalies', '--cleanup')
        self.assertEqual(MealAnomalyFlag.objects.count(), 0)
        self.assertEqual(MealDistributionEvent.objects.count(), history)  # only demo meals go
        self.assertEqual(PaymentTransaction.objects.count(), 0)
        self.assertEqual(BlockedServeAttempt.objects.count(), 0)

    def test_cleanup_leaves_real_flags_alone(self):
        real = meal_detection.flag_meal_event(self.make_event(hour=3))
        self.run_cmd('simulate_anomalies', '--school', str(self.school.id))
        self.run_cmd('simulate_anomalies', '--cleanup')
        self.assertTrue(MealAnomalyFlag.objects.filter(pk=real.pk).exists())
        self.assertTrue(MealDistributionEvent.objects.filter(pk=real.meal_event_id).exists())
