from django.test import TestCase
from meals.models import School, User, MealAccount
import bcrypt


def make_hashed(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def create_school(name, email):
    return School.objects.create(name=name, county='Nairobi', contact_email=email)


def create_user(school, role, name, email, password='Password123!'):
    return User.objects.create(
        school=school, role=role, full_name=name, email=email,
        hashed_password=make_hashed(password))


def get_token(client, email, password='Password123!'):
    res = client.post('/api/auth/login/', {
        'email': email, 'password': password
    }, content_type='application/json')
    return res.json()['tokens']['access']


class TestQRLookup(TestCase):
    def setUp(self):
        self.school = create_school('QR School', 'qr@test.com')
        self.kitchen = create_user(self.school, 'kitchen', 'Kitchen', 'kitchen@qr.test')
        self.kitchen_token = get_token(self.client, 'kitchen@qr.test')
        self.admin = create_user(self.school, 'admin', 'Admin', 'admin@qr.test')
        self.admin_token = get_token(self.client, 'admin@qr.test')

        self.student = create_user(self.school, 'student', 'Scan Student', 'scan@qr.test')
        self.meal_account = MealAccount.objects.create(
            student=self.student, balance_cents=10000)

    def test_kitchen_can_lookup_by_qr_token(self):
        res = self.client.get(
            f'/api/meals/lookup/?qr={self.meal_account.qr_token}',
            HTTP_AUTHORIZATION=f'Bearer {self.kitchen_token}')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['students'][0]['id'], self.student.id)

    def test_unrecognized_qr_token_returns_404(self):
        import uuid
        res = self.client.get(
            f'/api/meals/lookup/?qr={uuid.uuid4()}',
            HTTP_AUTHORIZATION=f'Bearer {self.kitchen_token}')
        self.assertEqual(res.status_code, 404)

    def test_malformed_qr_token_returns_404_not_500(self):
        res = self.client.get(
            '/api/meals/lookup/?qr=not-a-valid-uuid-at-all',
            HTTP_AUTHORIZATION=f'Bearer {self.kitchen_token}')
        self.assertEqual(res.status_code, 404)

    def test_qr_token_scoped_to_requesting_kitchens_school(self):
        other_school = create_school('Other QR School', 'otherqr@test.com')
        other_kitchen = create_user(
            other_school, 'kitchen', 'Other Kitchen', 'otherkitchen@qr.test')
        other_token = get_token(self.client, 'otherkitchen@qr.test')

        # A kitchen at a different school scanning this student's real
        # code should not find them (defense in depth, even though the
        # token itself is already globally unique).
        res = self.client.get(
            f'/api/meals/lookup/?qr={self.meal_account.qr_token}',
            HTTP_AUTHORIZATION=f'Bearer {other_token}')
        self.assertEqual(res.status_code, 404)

    def test_search_by_name_and_id_still_work(self):
        res = self.client.get(
            '/api/meals/lookup/?q=Scan',
            HTTP_AUTHORIZATION=f'Bearer {self.kitchen_token}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['count'], 1)

        res = self.client.get(
            f'/api/meals/lookup/?id={self.student.id}',
            HTTP_AUTHORIZATION=f'Bearer {self.kitchen_token}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['students'][0]['id'], self.student.id)

    def test_non_kitchen_cannot_use_qr_lookup(self):
        res = self.client.get(
            f'/api/meals/lookup/?qr={self.meal_account.qr_token}',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        self.assertEqual(res.status_code, 403)

    def test_admin_student_list_includes_qr_token(self):
        res = self.client.get(
            '/api/auth/admin/students/',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        self.assertEqual(res.status_code, 200)
        student_data = next(
            s for s in res.json() if s['id'] == self.student.id)
        self.assertEqual(student_data['qr_token'], str(self.meal_account.qr_token))

    def test_admin_can_regenerate_qr_token(self):
        old_token = self.meal_account.qr_token
        res = self.client.post(
            f'/api/auth/admin/students/{self.student.id}/regenerate-qr/',
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        self.assertEqual(res.status_code, 200)
        new_token = res.json()['qr_token']
        self.assertNotEqual(str(old_token), new_token)

        self.meal_account.refresh_from_db()
        self.assertEqual(str(self.meal_account.qr_token), new_token)

        # Old code no longer works
        res = self.client.get(
            f'/api/meals/lookup/?qr={old_token}',
            HTTP_AUTHORIZATION=f'Bearer {self.kitchen_token}')
        self.assertEqual(res.status_code, 404)

        # New code works
        res = self.client.get(
            f'/api/meals/lookup/?qr={new_token}',
            HTTP_AUTHORIZATION=f'Bearer {self.kitchen_token}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['students'][0]['id'], self.student.id)

    def test_non_admin_cannot_regenerate_qr(self):
        res = self.client.post(
            f'/api/auth/admin/students/{self.student.id}/regenerate-qr/',
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.kitchen_token}')
        self.assertEqual(res.status_code, 403)

    def test_qr_serve_flow_end_to_end(self):
        # Scan -> lookup finds student -> serve using existing endpoint
        # works exactly as if found by name search.
        from meals.models import MenuItem
        item = MenuItem.objects.create(
            school=self.school, name='Rice', price_cents=3000)

        lookup = self.client.get(
            f'/api/meals/lookup/?qr={self.meal_account.qr_token}',
            HTTP_AUTHORIZATION=f'Bearer {self.kitchen_token}')
        student_id = lookup.json()['students'][0]['id']

        res = self.client.post(
            '/api/meals/serve/',
            {'student_id': student_id, 'item_ids': [item.id]},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.kitchen_token}')
        self.assertEqual(res.status_code, 201)
        self.meal_account.refresh_from_db()
        self.assertEqual(self.meal_account.balance_cents, 7000)
