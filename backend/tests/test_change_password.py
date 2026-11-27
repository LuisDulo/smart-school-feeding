"""
School administrators create accounts and so know each initial password.
Users can now replace it. The current password is required, the new one must
pass the same rules as account creation, and every session issued before the
change stops working, so whoever knew the old password loses access.
"""
import bcrypt
from django.test import TestCase

from meals.models import School, User

OLD = 'Tr1cky-Meadow-Lamp'
NEW = 'Quiet-Harbour-Kettle9'
URL = '/api/auth/change-password/'


class TestChangePassword(TestCase):
    def setUp(self):
        school = School.objects.create(name='PW School', county='Nairobi',
                                       contact_email='pwc@test.com')
        self.user = User.objects.create(
            school=school, role='parent', full_name='Pat Parent', email='pat@pw.test',
            hashed_password=bcrypt.hashpw(OLD.encode(), bcrypt.gensalt()).decode())

    def login(self, password=OLD):
        return self.client.post('/api/auth/login/', {'email': 'pat@pw.test', 'password': password},
                                content_type='application/json')

    def change(self, access, current, new):
        return self.client.post(URL, {'current_password': current, 'new_password': new},
                                content_type='application/json',
                                HTTP_AUTHORIZATION=f'Bearer {access}')

    def profile(self, access):
        return self.client.get('/api/auth/profile/', HTTP_AUTHORIZATION=f'Bearer {access}')

    def test_password_is_changed_and_new_tokens_work(self):
        access = self.login().json()['tokens']['access']
        res = self.change(access, OLD, NEW)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.profile(res.json()['tokens']['access']).status_code, 200)
        self.assertEqual(self.login(NEW).status_code, 200)
        self.assertEqual(self.login(OLD).status_code, 401)

    def test_every_earlier_session_is_signed_out(self):
        other_device = self.login().json()['tokens']
        this_device = self.login().json()['tokens']
        self.assertEqual(self.change(this_device['access'], OLD, NEW).status_code, 200)
        self.assertEqual(self.profile(other_device['access']).status_code, 401)
        res = self.client.post('/api/auth/token/refresh/', {'refresh': other_device['refresh']},
                               content_type='application/json')
        self.assertEqual(res.status_code, 401)

    def test_wrong_current_password_is_refused(self):
        access = self.login().json()['tokens']['access']
        res = self.change(access, 'not-my-password', NEW)
        self.assertEqual(res.status_code, 400)
        self.assertIn('current_password', res.json())
        self.assertEqual(self.login(OLD).status_code, 200)

    def test_new_password_must_pass_the_rules(self):
        access = self.login().json()['tokens']['access']
        for weak in ('password123', '4829175630', 'Pat Parent'):
            res = self.change(access, OLD, weak)
            self.assertEqual(res.status_code, 400, weak)
            self.assertIn('new_password', res.json())

    def test_new_password_must_differ_from_the_current_one(self):
        access = self.login().json()['tokens']['access']
        res = self.change(access, OLD, OLD)
        self.assertEqual(res.status_code, 400)
        self.assertIn('new_password', res.json())

    def test_requires_sign_in(self):
        res = self.client.post(URL, {'current_password': OLD, 'new_password': NEW},
                               content_type='application/json')
        self.assertEqual(res.status_code, 401)
