from django.test import TestCase
from django.core.cache import cache


class TestLoginThrottle(TestCase):
    def setUp(self):
        cache.clear()

    def test_repeated_failed_logins_are_throttled(self):
        payload = {'email': 'nobody@example.com', 'password': 'WrongPass123!'}
        codes = [
            self.client.post('/api/auth/login/', payload,
                             content_type='application/json').status_code
            for _ in range(12)
        ]
        self.assertEqual(codes[:10], [401] * 10)
        self.assertIn(429, codes[10:])

    def tearDown(self):
        cache.clear()
