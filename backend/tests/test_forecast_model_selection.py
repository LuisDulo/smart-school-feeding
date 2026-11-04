from datetime import date, timedelta

import bcrypt
from django.test import TestCase

from forecasting import views as forecast_views
from meals.models import School, TermSchedule, User


def make_hashed(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


class TestAutomaticModelSelection(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name='Forecast School', county='Nairobi', contact_email='fc@test.com')
        TermSchedule.objects.create(
            school=self.school, term_name='Term 3',
            start_date=date.today() - timedelta(days=30),
            end_date=date.today() + timedelta(days=60), is_current=True)
        User.objects.create(
            school=self.school, role='admin', full_name='Fc Admin',
            email='fcadmin@test.com',
            hashed_password=make_hashed('Tr1cky-Meadow-Lamp'))
        login = self.client.post('/api/auth/login/', {
            'email': 'fcadmin@test.com', 'password': 'Tr1cky-Meadow-Lamp',
        }, content_type='application/json')
        self.auth = {'HTTP_AUTHORIZATION': f"Bearer {login.json()['tokens']['access']}"}

    def _generate(self, body):
        return self.client.post('/api/forecast/generate/', body,
                                content_type='application/json', **self.auth)

    def test_generate_uses_the_best_model(self):
        res = self._generate({'horizon': 'five_day'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['model_key'], forecast_views.DEFAULT_MODEL_KEY)

    def test_client_supplied_model_is_ignored(self):
        other = next(k for k in forecast_views.MODELS
                     if k != forecast_views.DEFAULT_MODEL_KEY
                     and forecast_views.MODELS[k]['loaded'])
        res = self._generate({'model': other, 'horizon': 'five_day'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['model_key'], forecast_views.DEFAULT_MODEL_KEY)

    def test_unknown_model_value_does_not_error(self):
        res = self._generate({'model': 'does_not_exist', 'horizon': 'five_day'})
        self.assertEqual(res.status_code, 200)

    def test_active_model_endpoint_reports_the_best_model(self):
        res = self.client.get('/api/forecast/active-model/', **self.auth)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body['key'], forecast_views.DEFAULT_MODEL_KEY)
        self.assertEqual(body['name'],
                         forecast_views.MODELS[forecast_views.DEFAULT_MODEL_KEY]['name'])
        self.assertIsNotNone(body['test_mae'])

    def test_active_model_requires_authentication(self):
        self.assertEqual(
            self.client.get('/api/forecast/active-model/').status_code, 401)
