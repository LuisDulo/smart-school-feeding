"""
Menu items, meal combinations and meal serving must answer bad input with a
clear 400 (never a 500), and must refuse blank or oversized names.
"""
import bcrypt
from django.test import TestCase

from meals.models import MealAccount, MealCombo, MenuItem, School, User

PASSWORD = 'Tr1cky-Meadow-Lamp'


def hashed():
    return bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt()).decode()


class TestMenuValidation(TestCase):
    def setUp(self):
        self._tokens = {}
        self.school =School.objects.create(name='S', county='N', contact_email='s@t.com')
        self.other = School.objects.create(name='O', county='N', contact_email='o@t.com')
        for role in ('admin', 'kitchen'):
            User.objects.create(school=self.school, role=role, full_name=role,
                                email=f'{role}@t.com', hashed_password=hashed())
        User.objects.create(school=self.other, role='kitchen', full_name='ok',
                            email='okitchen@t.com', hashed_password=hashed())
        self.student = User.objects.create(school=self.school, role='student', full_name='Pupil',
                                           email='pupil@t.com', hashed_password=hashed())
        MealAccount.objects.create(student=self.student, balance_cents=100000)
        self.rice = MenuItem.objects.create(school=self.school, name='Rice', price_cents=3000)
        self.beans = MenuItem.objects.create(school=self.school, name='Beans', price_cents=2000)
        self.other_item = MenuItem.objects.create(school=self.other, name='Ugali', price_cents=2500)

    def _auth(self, email):
        # Log in once per user: the login endpoint is throttled to 10/minute.
        if email not in self._tokens:
            res = self.client.post('/api/auth/login/', {'email': email, 'password': PASSWORD},
                                   content_type='application/json')
            self._tokens[email] = res.json()['tokens']['access']
        return {'HTTP_AUTHORIZATION': f'Bearer {self._tokens[email]}'}

    def call(self, method, url, email='admin@t.com', body=None):
        return getattr(self.client, method)(url, body if body is not None else {},
                                            content_type='application/json',
                                            **self._auth(email))

    # ---- menu items ------------------------------------------------------
    def test_create_menu_item_ok(self):
        res = self.call('post', '/api/meals/menu/', body={'name': ' Chapati ', 'price_cents': 1500})
        self.assertEqual(res.status_code, 201)
        self.assertTrue(MenuItem.objects.filter(school=self.school, name='Chapati').exists())

    def test_create_menu_item_rejects_bad_names(self):
        for name in (None, '', '   ', 123, ['x'], 'x' * 101):
            res = self.call('post', '/api/meals/menu/', body={'name': name, 'price_cents': 100})
            self.assertEqual(res.status_code, 400, repr(name))

    def test_edit_menu_item_cannot_be_blanked_or_oversized(self):
        for name in ('', '   ', None, 'x' * 150):
            res = self.call('patch', f'/api/meals/menu/{self.rice.id}/', body={'name': name})
            self.assertEqual(res.status_code, 400, repr(name))
        self.rice.refresh_from_db()
        self.assertEqual(self.rice.name, 'Rice')

    # ---- combos ----------------------------------------------------------
    def test_create_combo_ok(self):
        res = self.call('post', '/api/meals/combos/',
                        body={'name': 'Lunch', 'item_ids': [self.rice.id, self.beans.id]})
        self.assertEqual(res.status_code, 201)
        combo = MealCombo.objects.get(school=self.school, name='Lunch')
        self.assertEqual(combo.items.count(), 2)

    def test_create_combo_accepts_duplicate_and_string_ids(self):
        res = self.call('post', '/api/meals/combos/',
                        body={'name': 'Dup', 'item_ids': [self.rice.id, str(self.rice.id)]})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(MealCombo.objects.get(name='Dup').items.count(), 1)

    def test_create_combo_rejects_bad_input_with_400(self):
        cases = [
            {'name': None, 'item_ids': [self.rice.id]},
            {'name': '  ', 'item_ids': [self.rice.id]},
            {'name': 'x' * 150, 'item_ids': [self.rice.id]},
            {'name': 'NoItems', 'item_ids': []},
            {'name': 'NoItems'},
            {'name': 'Bad', 'item_ids': 'oops'},
            {'name': 'Bad', 'item_ids': 5},
            {'name': 'Bad', 'item_ids': {'a': 1}},
            {'name': 'Bad', 'item_ids': ['abc']},
            {'name': 'Bad', 'item_ids': [None]},
            {'name': 'Bad', 'item_ids': [[1]]},
            {'name': 'Bad', 'item_ids': [True]},
            {'name': 'Bad', 'item_ids': [999999]},
            {'name': 'Bad', 'item_ids': [self.other_item.id]},
        ]
        for body in cases:
            res = self.call('post', '/api/meals/combos/', body=body)
            self.assertEqual(res.status_code, 400, body)
        self.assertEqual(MealCombo.objects.count(), 0)

    def test_edit_combo_validation(self):
        combo = MealCombo.objects.create(school=self.school, name='Base')
        combo.items.add(self.rice)
        url = f'/api/meals/combos/{combo.id}/'
        for body in ({'name': ''}, {'name': 'x' * 101}, {'item_ids': 'oops'},
                     {'item_ids': []}, {'item_ids': [self.other_item.id]}):
            self.assertEqual(self.call('patch', url, body=body).status_code, 400, body)
        res = self.call('patch', url, body={'name': 'Renamed', 'item_ids': [self.beans.id]})
        self.assertEqual(res.status_code, 200)
        combo.refresh_from_db()
        self.assertEqual(combo.name, 'Renamed')
        self.assertEqual([i.id for i in combo.items.all()], [self.beans.id])

    # ---- serving ---------------------------------------------------------
    def test_serve_meal_rejects_malformed_item_ids(self):
        for ids in ('oops', 7, ['abc'], [None], {'a': 1}):
            res = self.call('post', '/api/meals/serve/', 'kitchen@t.com',
                            {'student_id': self.student.id, 'item_ids': ids})
            self.assertEqual(res.status_code, 400, repr(ids))

    def test_serve_meal_rejects_malformed_student_id(self):
        for sid in ('abc', [1], {'a': 1}):
            res = self.call('post', '/api/meals/serve/', 'kitchen@t.com',
                            {'student_id': sid, 'item_ids': [self.rice.id]})
            self.assertIn(res.status_code, (400, 404), repr(sid))

    def test_serve_meal_ok_and_deducts(self):
        res = self.call('post', '/api/meals/serve/', 'kitchen@t.com',
                        {'student_id': self.student.id, 'item_ids': [self.rice.id, self.beans.id]})
        self.assertEqual(res.status_code, 201, res.content)
        self.student.meal_account.refresh_from_db()
        self.assertEqual(self.student.meal_account.balance_cents, 95000)

    def test_kitchen_of_another_school_cannot_serve_this_student(self):
        """Even using their own school's menu items."""
        res = self.call('post', '/api/meals/serve/', 'okitchen@t.com',
                        {'student_id': self.student.id, 'item_ids': [self.other_item.id]})
        self.assertEqual(res.status_code, 404)
        self.student.meal_account.refresh_from_db()
        self.assertEqual(self.student.meal_account.balance_cents, 100000)
