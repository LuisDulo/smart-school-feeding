"""
Payment flags come from the payment Isolation Forest, which flags at a score
of 0.50 and rarely scores above 0.65, so sharing the meal bands (medium 0.65,
high 0.80) made every real payment flag LOW. Payment flags now have bands on
the model's own scale, and every view uses the same definition.
"""
import bcrypt
from django.test import TestCase

from anomalies.severity import meal_severity, payment_severity
from meals.models import AnomalyFlag, MealAccount, PaymentTransaction, School, User

PASSWORD = 'Password123!'


def make_user(school, role, name, email):
    return User.objects.create(
        school=school, role=role, full_name=name, email=email,
        hashed_password=bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt()).decode())


class TestSeverityBands(TestCase):
    def test_payment_bands_follow_the_payment_model_scale(self):
        # scores the model gave the demo cases
        self.assertEqual(payment_severity(0.5337), 'LOW')     # burst of small top-ups
        self.assertEqual(payment_severity(0.5915), 'MEDIUM')  # KES 25,000 top-up
        self.assertEqual(payment_severity(0.6277), 'HIGH')    # KES 12,000 at 03:12

    def test_meal_bands_are_unchanged(self):
        self.assertEqual(meal_severity(0.51), 'LOW')
        self.assertEqual(meal_severity(0.70), 'MEDIUM')
        self.assertEqual(meal_severity(0.80), 'HIGH')


class TestSeverityInTheApi(TestCase):
    def setUp(self):
        self.school = School.objects.create(name='Sev School', county='Nairobi',
                                            contact_email='sev@test.com')
        wk = School.objects.create(name='Webmasters Kenya', county='Nairobi',
                                   contact_email='wk@test.com')
        make_user(self.school, 'bursar', 'Sev Bursar', 'bursar@sev.test')
        make_user(wk, 'superadmin', 'Sev Super', 'super@sev.test')
        student = make_user(self.school, 'student', 'Sev Student', 'student@sev.test')
        account = MealAccount.objects.create(student=student, balance_cents=0)
        for i, score in enumerate((0.52, 0.58, 0.63)):
            tx = PaymentTransaction.objects.create(
                meal_account=account, amount_cents=100000, status='confirmed',
                mpesa_reference=f'ws_CO_SEV{i}')
            AnomalyFlag.objects.create(transaction=tx, anomaly_score=score)

    def get(self, url, email):
        token = self.client.post('/api/auth/login/', {'email': email, 'password': PASSWORD},
                                 content_type='application/json').json()['tokens']['access']
        return self.client.get(url, HTTP_AUTHORIZATION=f'Bearer {token}').json()

    def test_school_queue_labels_and_counts_payment_flags(self):
        body = self.get('/api/anomalies/flags/', 'bursar@sev.test')
        self.assertEqual(sorted(f['severity'] for f in body['flags']), ['HIGH', 'LOW', 'MEDIUM'])
        self.assertEqual(body['high_severity'], 1)

    def test_network_view_filters_with_the_same_bands(self):
        body = self.get('/api/superadmin/anomalies/?severity=HIGH', 'super@sev.test')
        self.assertEqual([f['anomaly_score'] for f in body['flags']], [0.63])
        self.assertEqual(body['high_severity'], 1)


class TestNetworkMealFlags(TestCase):
    """The network Anomaly Flags page read only payment flags; meal-serving
    flags from every school now appear under ?type=meal."""

    def setUp(self):
        from datetime import date
        from meals.models import MealAnomalyFlag
        wk = School.objects.create(name='Webmasters Kenya', county='Nairobi',
                                   contact_email='wk2@test.com')
        make_user(wk, 'superadmin', 'Net Super', 'super@net.test')
        for n, score in ((1, 0.85), (2, 0.51)):
            school = School.objects.create(name=f'Net School {n}', county='Nairobi',
                                           contact_email=f'net{n}@test.com')
            student = make_user(school, 'student', f'Net Student {n}', f'student{n}@net.test')
            account = MealAccount.objects.create(student=student, balance_cents=0)
            MealAnomalyFlag.objects.create(
                school=school, meal_account=account, kind='pattern', flag_date=date.today(),
                anomaly_score=score, reasons=[f'reason {n}'])

    def get(self, url):
        token = self.client.post('/api/auth/login/', {'email': 'super@net.test', 'password': PASSWORD},
                                 content_type='application/json').json()['tokens']['access']
        return self.client.get(url, HTTP_AUTHORIZATION=f'Bearer {token}').json()

    def test_meal_flags_from_every_school_are_listed(self):
        body = self.get('/api/superadmin/anomalies/?type=meal&reviewed=')
        self.assertEqual(body['total'], 2)
        self.assertEqual({f['school'] for f in body['flags']}, {'Net School 1', 'Net School 2'})
        self.assertEqual({f['severity'] for f in body['flags']}, {'HIGH', 'LOW'})
        self.assertEqual(body['high_severity'], 1)
        self.assertIn('reason 1', [r for f in body['flags'] for r in f['reasons']])

    def test_payment_view_is_unchanged_by_default(self):
        self.assertEqual(self.get('/api/superadmin/anomalies/')['total'], 0)
