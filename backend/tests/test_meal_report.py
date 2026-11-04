import csv
import io
from datetime import date, timedelta

import bcrypt
from django.test import TestCase
from django.utils import timezone

from meals.models import (MealAccount, MealDistributionEvent, MenuItem,
                          PaymentTransaction, School, User)

PASSWORD = 'Tr1cky-Meadow-Lamp'


def make_hashed(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


class TestMealReportDownload(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name='Report School', county='Nairobi', contact_email='rep@test.com')
        self.kitchen = User.objects.create(
            school=self.school, role='kitchen', full_name='Mary Cook',
            email='cook@rep.test', hashed_password=make_hashed(PASSWORD))
        self.parent = User.objects.create(
            school=self.school, role='parent', full_name='Pat Parent',
            email='parent@rep.test', hashed_password=make_hashed(PASSWORD))
        self.other_parent = User.objects.create(
            school=self.school, role='parent', full_name='Olu Other',
            email='other@rep.test', hashed_password=make_hashed(PASSWORD))
        self.child = User.objects.create(
            school=self.school, role='student', full_name='Amina Wanjiru',
            email='amina@rep.test', hashed_password=make_hashed(PASSWORD))
        self.account = MealAccount.objects.create(student=self.child, balance_cents=250000)
        self.account.guardians.add(self.parent)
        other_child = User.objects.create(
            school=self.school, role='student', full_name='Not Mine',
            email='notmine@rep.test', hashed_password=make_hashed(PASSWORD))
        self.other_account = MealAccount.objects.create(student=other_child, balance_cents=1000)
        self.other_account.guardians.add(self.other_parent)

        rice = MenuItem.objects.create(school=self.school, name='Rice', price_cents=3000)
        beans = MenuItem.objects.create(school=self.school, name='Beans', price_cents=3000)
        self.event = MealDistributionEvent.objects.create(
            meal_account=self.account, recorded_by=self.kitchen,
            amount_cents=6000, meal_date=date.today(), meals_served=1)
        self.event.items.set([rice, beans])
        tx = PaymentTransaction.objects.create(
            meal_account=self.account, amount_cents=50000,
            mpesa_reference='RCV1', status='confirmed')
        PaymentTransaction.objects.filter(pk=tx.pk).update(created_at=timezone.now())

        login = self.client.post('/api/auth/login/', {
            'email': 'parent@rep.test', 'password': PASSWORD},
            content_type='application/json')
        self.auth = {'HTTP_AUTHORIZATION': f"Bearer {login.json()['tokens']['access']}"}

    def _get(self, **params):
        return self.client.get('/api/payments/meal-report/', params, **self.auth)

    def test_pdf_is_a_downloadable_pdf(self):
        res = self._get(months=3, file_format='pdf')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/pdf')
        self.assertTrue(res.content.startswith(b'%PDF'))
        disposition = res['Content-Disposition']
        self.assertIn('attachment', disposition)
        self.assertIn('meal-report-amina-wanjiru-', disposition)
        self.assertTrue(disposition.endswith('.pdf"'))

    def test_pdf_is_the_default_format(self):
        res = self.client.get('/api/payments/meal-report/', **self.auth)
        self.assertEqual(res['Content-Type'], 'application/pdf')

    def test_csv_contains_summary_and_each_meal(self):
        res = self._get(months=3, file_format='csv')
        self.assertEqual(res.status_code, 200)
        self.assertIn('text/csv', res['Content-Type'])
        self.assertIn('.csv"', res['Content-Disposition'])
        text = res.content.decode('utf-8-sig')
        rows = list(csv.reader(io.StringIO(text)))
        flat = [cell for row in rows for cell in row]
        self.assertIn('Amina Wanjiru', flat)
        self.assertIn('Report School', flat)
        self.assertIn('Beans, Rice', flat)
        self.assertIn('Mary Cook', flat)
        self.assertIn('60.00', flat)           # the meal amount
        self.assertIn('2,500.00', flat)        # current balance

    def test_csv_totals_match_the_on_screen_report(self):
        report = self.client.get('/api/payments/monthly-report/?months=3',
                                 **self.auth).json()
        text = self._get(months=3, file_format='csv').content.decode('utf-8-sig')
        total_row = next(r for r in csv.reader(io.StringIO(text)) if r and r[0] == 'Total')
        self.assertEqual(int(total_row[1]),
                         sum(m['meals_collected'] for m in report['monthly_data']))

    def test_monthly_report_response_shape_is_unchanged(self):
        report = self.client.get('/api/payments/monthly-report/?months=2',
                                 **self.auth).json()
        self.assertEqual(len(report['monthly_data']), 2)
        self.assertNotIn('month_start', report['monthly_data'][0])
        self.assertEqual(report['total_meals_this_month'], 1)

    def test_invalid_format_is_rejected(self):
        self.assertEqual(self._get(file_format='docx').status_code, 400)

    def test_invalid_months_is_rejected(self):
        self.assertEqual(self._get(months='abc').status_code, 400)

    def test_parent_cannot_download_another_childs_report(self):
        res = self._get(meal_account_id=self.other_account.id, file_format='csv')
        self.assertEqual(res.status_code, 404)

    def test_requires_authentication(self):
        self.assertEqual(self.client.get('/api/payments/meal-report/').status_code, 401)

    def test_report_with_no_meals_still_generates(self):
        MealDistributionEvent.objects.all().delete()
        res = self._get(file_format='pdf')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.content.startswith(b'%PDF'))
