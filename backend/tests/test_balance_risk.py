"""
A student who has already run out of money is refused meals, so they have no
recent meal history. The days-remaining estimate used to divide the balance
by zero spending and return 999 days, so the classifier called exactly these
students safe. Without meal history the estimate now assumes one meal per
school day, so an empty balance reads as at risk on both the dashboard and
the parent's app.
"""
from datetime import date, timedelta

import bcrypt
from django.test import TestCase

from forecasting import views as forecasting
from meals.models import (MealAccount, MealDistributionEvent, PaymentTransaction,
                          School, User)

PASSWORD = 'Password123!'


def make_user(school, role, name, email):
    return User.objects.create(
        school=school, role=role, full_name=name, email=email,
        hashed_password=bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt()).decode())


class TestBalanceRiskForDepletedStudents(TestCase):
    def setUp(self):
        if not forecasting.RISK_LOADED:
            self.skipTest('balance risk classifier not available')
        self.school = School.objects.create(
            name='Risk School', county='Nairobi', contact_email='risk@test.com')
        self.admin = make_user(self.school, 'admin', 'Risk Admin', 'admin@risk.test')
        self.parent = make_user(self.school, 'parent', 'Risk Parent', 'parent@risk.test')

        empty = make_user(self.school, 'student', 'Empty Student', 'empty@risk.test')
        self.empty_account = MealAccount.objects.create(student=empty, balance_cents=0)
        self.empty_account.guardians.add(self.parent)

        healthy = make_user(self.school, 'student', 'Healthy Student', 'healthy@risk.test')
        self.healthy_account = MealAccount.objects.create(student=healthy, balance_cents=500000)
        today = date.today()
        for i in range(1, 15):
            day = today - timedelta(days=i)
            if day.weekday() < 5:
                MealDistributionEvent.objects.create(
                    meal_account=self.healthy_account, meal_date=day, meals_served=1,
                    amount_cents=5000)
        PaymentTransaction.objects.create(
            meal_account=self.healthy_account, amount_cents=500000,
            status='confirmed', mpesa_reference='ws_CO_RISK1')

    def token(self, email):
        res = self.client.post('/api/auth/login/', {'email': email, 'password': PASSWORD},
                               content_type='application/json')
        return res.json()['tokens']['access']

    def test_empty_balance_without_meals_is_not_estimated_to_last_forever(self):
        _, display = forecasting._risk_features_for(self.empty_account, date.today())
        self.assertEqual(display['estimated_days_remaining'], 0)

    def test_dashboard_lists_the_empty_account_as_at_risk(self):
        res = self.client.get('/api/forecast/risk/',
                              HTTP_AUTHORIZATION=f'Bearer {self.token("admin@risk.test")}')
        self.assertEqual(res.status_code, 200)
        at_risk = {s['student_name'] for s in res.json()['at_risk_students']}
        self.assertIn('Empty Student', at_risk)
        self.assertNotIn('Healthy Student', at_risk)

    def test_parent_app_warns_about_the_empty_account(self):
        res = self.client.get(
            f'/api/payments/risk-score/?meal_account_id={self.empty_account.id}',
            HTTP_AUTHORIZATION=f'Bearer {self.token("parent@risk.test")}')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()['at_risk'])
        self.assertEqual(res.json()['model'], 'random_forest_classifier')
