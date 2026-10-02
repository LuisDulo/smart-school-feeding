import bcrypt
from django.test import TestCase
from meals.models import School, User


class TestRefreshTokenBlacklisting(TestCase):
    def setUp(self):
        school = School.objects.create(
            name='Tok School', county='Nairobi', contact_email='tok@test.com')
        User.objects.create(
            school=school, role='parent', full_name='Tok Parent',
            email='tok@parent.test',
            hashed_password=bcrypt.hashpw(b'Tr1cky-Meadow-Lamp',
                                          bcrypt.gensalt()).decode())
        res = self.client.post('/api/auth/login/', {
            'email': 'tok@parent.test', 'password': 'Tr1cky-Meadow-Lamp',
        }, content_type='application/json')
        self.tokens = res.json()['tokens']

    def _refresh(self, token):
        return self.client.post('/api/auth/token/refresh/', {'refresh': token},
                                content_type='application/json')

    def test_refresh_returns_new_pair(self):
        res = self._refresh(self.tokens['refresh'])
        self.assertEqual(res.status_code, 200)
        self.assertNotEqual(res.json()['refresh'], self.tokens['refresh'])

    def test_rotated_refresh_token_cannot_be_reused(self):
        self.assertEqual(self._refresh(self.tokens['refresh']).status_code, 200)
        self.assertEqual(self._refresh(self.tokens['refresh']).status_code, 401)

    def test_new_refresh_token_still_works(self):
        new = self._refresh(self.tokens['refresh']).json()['refresh']
        self.assertEqual(self._refresh(new).status_code, 200)

    def test_logout_revokes_refresh_token(self):
        res = self.client.post(
            '/api/auth/logout/', {'refresh': self.tokens['refresh']},
            content_type='application/json',
            HTTP_AUTHORIZATION=f"Bearer {self.tokens['access']}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self._refresh(self.tokens['refresh']).status_code, 401)

    def test_garbage_refresh_token_rejected(self):
        self.assertEqual(self._refresh('not-a-token').status_code, 401)
