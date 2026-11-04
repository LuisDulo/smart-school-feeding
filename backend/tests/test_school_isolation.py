"""
A school's staff must never be able to read or change another school's data,
even by guessing ids. Each test acts as school B's admin/kitchen/parent
against objects that belong to school A.
"""
import bcrypt
from django.test import TestCase

from meals.models import (AnomalyFlag, CreditRequest, MealAccount, MealCombo,
                          MenuItem, PaymentTransaction, School, SupportIssue, User)

PASSWORD = 'Tr1cky-Meadow-Lamp'


def hashed(p=PASSWORD):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


class TestSchoolIsolation(TestCase):
    def setUp(self):
        self.a = School.objects.create(name='School A', county='N', contact_email='a@t.com')
        self.b = School.objects.create(name='School B', county='N', contact_email='b@t.com')

        # school A data
        self.a_student = User.objects.create(school=self.a, role='student', full_name='A Pupil',
                                             email='apupil@t.com', hashed_password=hashed())
        self.a_account = MealAccount.objects.create(student=self.a_student, balance_cents=100000)
        self.a_parent = User.objects.create(school=self.a, role='parent', full_name='A Parent',
                                            email='aparent@t.com', hashed_password=hashed())
        self.a_account.guardians.add(self.a_parent)
        self.a_item = MenuItem.objects.create(school=self.a, name='A Rice', price_cents=3000)
        self.a_combo = MealCombo.objects.create(school=self.a, name='A Combo')
        self.a_combo.items.add(self.a_item)
        tx = PaymentTransaction.objects.create(meal_account=self.a_account, amount_cents=5000,
                                               mpesa_reference='X1', status='confirmed')
        self.a_flag = AnomalyFlag.objects.create(transaction=tx, anomaly_score=-0.5)
        self.a_credit = CreditRequest.objects.create(
            meal_account=self.a_account, requested_by=self.a_parent, requested_amount_cents=10000)
        self.a_issue = SupportIssue.objects.create(
            raised_by=self.a_parent, meal_account=self.a_account, category='other',
            subject='A issue', description='d')

        # school B staff
        for role in ('admin', 'kitchen', 'bursar', 'parent'):
            User.objects.create(school=self.b, role=role, full_name=f'B {role}',
                                email=f'b{role}@t.com', hashed_password=hashed())
        self.b_parent = User.objects.get(email='bparent@t.com')

    def _auth(self, email):
        res = self.client.post('/api/auth/login/', {'email': email, 'password': PASSWORD},
                               content_type='application/json')
        return {'HTTP_AUTHORIZATION': f"Bearer {res.json()['tokens']['access']}"}

    def _json(self, method, url, email, body=None):
        return getattr(self.client, method)(url, body or {}, content_type='application/json',
                                            **self._auth(email))

    def test_other_schools_menu_item_is_untouchable(self):
        self.assertEqual(self._json('patch', f'/api/meals/menu/{self.a_item.id}/',
                                    'badmin@t.com', {'name': 'hacked'}).status_code, 404)
        self.assertEqual(self._json('delete', f'/api/meals/menu/{self.a_item.id}/',
                                    'badmin@t.com').status_code, 404)
        self.a_item.refresh_from_db()
        self.assertEqual(self.a_item.name, 'A Rice')
        self.assertTrue(self.a_item.is_active)

    def test_other_schools_combo_is_untouchable(self):
        self.assertEqual(self._json('patch', f'/api/meals/combos/{self.a_combo.id}/',
                                    'badmin@t.com', {'name': 'hacked'}).status_code, 404)
        self.assertEqual(self._json('delete', f'/api/meals/combos/{self.a_combo.id}/',
                                    'badmin@t.com').status_code, 404)

    def test_cannot_build_a_combo_from_another_schools_items(self):
        res = self._json('post', '/api/meals/combos/', 'badmin@t.com',
                         {'name': 'steal', 'item_ids': [self.a_item.id]})
        self.assertEqual(res.status_code, 400)

    def test_other_schools_anomaly_flag_cannot_be_reviewed(self):
        res = self._json('post', f'/api/anomalies/flags/{self.a_flag.id}/review/',
                         'badmin@t.com', {'action': 'legitimate'})
        self.assertEqual(res.status_code, 404)
        self.a_flag.refresh_from_db()
        self.assertFalse(self.a_flag.reviewed)

    def test_other_schools_credit_request_cannot_be_approved(self):
        res = self._json('post', f'/api/payments/credit-requests/{self.a_credit.id}/review/',
                         'badmin@t.com', {'action': 'approved'})
        self.assertEqual(res.status_code, 404)
        self.a_account.refresh_from_db()
        self.assertEqual(self.a_account.credit_limit_cents, 0)

    def test_other_schools_support_issue_cannot_be_resolved(self):
        res = self._json('post', f'/api/support/issues/{self.a_issue.id}/resolve/',
                         'badmin@t.com', {'status': 'resolved'})
        self.assertEqual(res.status_code, 404)

    def test_other_schools_student_qr_cannot_be_regenerated(self):
        before = self.a_account.qr_token
        res = self._json('post', f'/api/auth/admin/students/{self.a_student.id}/regenerate-qr/',
                         'badmin@t.com')
        self.assertEqual(res.status_code, 404)
        self.a_account.refresh_from_db()
        self.assertEqual(self.a_account.qr_token, before)

    def test_cannot_link_a_guardian_to_another_schools_student(self):
        res = self._json('post', '/api/auth/admin/link/', 'badmin@t.com',
                         {'parent_id': self.b_parent.id, 'student_id': self.a_student.id})
        self.assertIn(res.status_code, (400, 404))
        self.assertFalse(self.a_account.guardians.filter(id=self.b_parent.id).exists())

    def test_kitchen_cannot_serve_another_schools_student(self):
        res = self._json('post', '/api/meals/serve/', 'bkitchen@t.com',
                         {'student_id': self.a_student.id, 'item_ids': [self.a_item.id]})
        self.assertIn(res.status_code, (400, 404))
        self.a_account.refresh_from_db()
        self.assertEqual(self.a_account.balance_cents, 100000)

    def test_kitchen_cannot_look_up_another_schools_student_by_qr(self):
        res = self.client.get(f'/api/meals/lookup/?qr={self.a_account.qr_token}',
                              **self._auth('bkitchen@t.com'))
        body = res.json()
        found = body if isinstance(body, list) else body.get('results', body.get('students', []))
        self.assertNotIn(self.a_student.id, [r.get('id', r.get('student_id')) for r in found])

    def test_balance_lists_only_show_own_school(self):
        res = self.client.get('/api/payments/balances/', **self._auth('badmin@t.com'))
        self.assertEqual(res.status_code, 200)
        self.assertNotIn('A Pupil', res.content.decode())

    def test_parent_cannot_read_another_parents_child(self):
        for path in ('balance', 'monthly-report', 'balance-trend', 'risk-score', 'activity'):
            res = self.client.get(f'/api/payments/{path}/?meal_account_id={self.a_account.id}',
                                  **self._auth('bparent@t.com'))
            self.assertEqual(res.status_code, 404, path)
        res = self.client.get(f'/api/meals/consumption/?meal_account_id={self.a_account.id}',
                              **self._auth('bparent@t.com'))
        self.assertEqual(res.status_code, 404)
        res = self.client.get(f'/api/meals/qr/?meal_account_id={self.a_account.id}',
                              **self._auth('bparent@t.com'))
        self.assertEqual(res.status_code, 404)

    def test_parent_cannot_see_the_daily_meal_log(self):
        """The log lists every student's meals and balances: staff only."""
        res = self.client.get('/api/meals/log/', **self._auth('aparent@t.com'))
        self.assertEqual(res.status_code, 403)

    # ---- payment status ------------------------------------------------
    def test_payment_status_visible_to_owner_guardian_and_same_school_staff(self):
        tx = PaymentTransaction.objects.filter(meal_account=self.a_account).first()
        User.objects.create(school=self.a, role='admin', full_name='A Admin',
                            email='aadmin@t.com', hashed_password=hashed())
        for email in ('aparent@t.com', 'apupil@t.com', 'aadmin@t.com'):
            res = self.client.get(f'/api/payments/status/{tx.id}/', **self._auth(email))
            self.assertEqual(res.status_code, 200, email)

    def test_payment_status_hidden_from_other_families_and_schools(self):
        tx = PaymentTransaction.objects.filter(meal_account=self.a_account).first()
        for email in ('bparent@t.com', 'badmin@t.com', 'bbursar@t.com', 'bkitchen@t.com'):
            res = self.client.get(f'/api/payments/status/{tx.id}/', **self._auth(email))
            self.assertEqual(res.status_code, 404, email)

    # ---- anomaly scoring ---------------------------------------------------
    def test_parent_cannot_score_transactions(self):
        tx = PaymentTransaction.objects.filter(meal_account=self.a_account).first()
        res = self._json('post', '/api/anomalies/score/', 'aparent@t.com',
                         {'transaction_id': tx.id})
        self.assertEqual(res.status_code, 403)

    def test_other_schools_transaction_cannot_be_scored(self):
        tx = PaymentTransaction.objects.filter(meal_account=self.a_account).first()
        res = self._json('post', '/api/anomalies/score/', 'badmin@t.com',
                         {'transaction_id': tx.id})
        self.assertEqual(res.status_code, 404)

    # ---- forecasts are staff-only -------------------------------------------
    def test_parents_cannot_use_forecast_endpoints(self):
        auth = self._auth('aparent@t.com')
        for path in ('history', 'stats', 'active-model'):
            self.assertEqual(self.client.get(f'/api/forecast/{path}/', **auth).status_code,
                             403, path)
        res = self._json('post', '/api/forecast/generate/', 'aparent@t.com',
                         {'horizon': 'five_day'})
        self.assertEqual(res.status_code, 403)

    def test_school_staff_can_still_use_forecast_endpoints(self):
        for email in ('badmin@t.com', 'bbursar@t.com', 'bkitchen@t.com'):
            auth = self._auth(email)
            for path in ('history', 'stats', 'active-model'):
                self.assertEqual(
                    self.client.get(f'/api/forecast/{path}/', **auth).status_code, 200,
                    f'{email} {path}')

    def test_staff_can_still_read_the_daily_meal_log(self):
        for email in ('badmin@t.com', 'bbursar@t.com', 'bkitchen@t.com'):
            res = self.client.get('/api/meals/log/', **self._auth(email))
            self.assertEqual(res.status_code, 200, email)
