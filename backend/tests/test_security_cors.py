from django.test import TestCase, override_settings


@override_settings(CORS_ALLOW_ALL_ORIGINS=False,
                   CORS_ALLOWED_ORIGINS=['https://dashboard.example.com'])
class TestCorsAllowList(TestCase):
    def test_allowed_origin_gets_cors_header(self):
        res = self.client.get('/api/auth/schools/',
                              HTTP_ORIGIN='https://dashboard.example.com')
        self.assertEqual(res['Access-Control-Allow-Origin'],
                         'https://dashboard.example.com')

    def test_unknown_origin_gets_no_cors_header(self):
        res = self.client.get('/api/auth/schools/',
                              HTTP_ORIGIN='https://evil.example.com')
        self.assertNotIn('Access-Control-Allow-Origin', res)
