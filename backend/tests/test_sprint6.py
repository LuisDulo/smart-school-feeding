from django.test import TestCase
from meals.models import (School, User, MealAccount, MenuItem, MealCombo,
                           CreditRequest, SupportIssue,
                           MealDistributionEvent)
import bcrypt


def make_hashed(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def create_school(name='Test School', email='test@school.com'):
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


# ════════════════════════════════════════
# ADMIN ACCOUNT CREATION + PARENT LINKING
# ════════════════════════════════════════

class TestAdminAccountCreation(TestCase):
    def setUp(self):
        self.school = create_school('Link School', 'link@test.com')
        self.admin = create_user(self.school, 'admin', 'Admin', 'linkadmin@test.com')
        self.token = get_token(self.client, 'linkadmin@test.com')

    def test_admin_creates_student_with_meal_account(self):
        res = self.client.post(
            '/api/auth/admin/students/',
            {'full_name': 'New Student', 'email': 'newstu@test.com',
             'password': 'Password123!', 'starting_balance_cents': 20000},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 201)
        student = User.objects.get(email='newstu@test.com')
        self.assertEqual(student.role, 'student')
        self.assertEqual(student.meal_account.balance_cents, 20000)

    def test_admin_creates_parent_and_links_to_student(self):
        student = create_user(self.school, 'student', 'Kid', 'kid@test.com')
        MealAccount.objects.create(student=student, balance_cents=0)

        res = self.client.post(
            '/api/auth/admin/parents/',
            {'full_name': 'New Parent', 'email': 'newparent@test.com',
             'password': 'Password123!', 'student_ids': [student.id]},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 201)
        parent = User.objects.get(email='newparent@test.com')
        self.assertIn(parent, student.meal_account.guardians.all())

    def test_link_existing_parent_to_existing_student(self):
        student = create_user(self.school, 'student', 'Kid2', 'kid2@test.com')
        MealAccount.objects.create(student=student, balance_cents=5000)
        parent = create_user(self.school, 'parent', 'Parent2', 'parent2@test.com')

        res = self.client.post(
            '/api/auth/admin/link/',
            {'parent_id': parent.id, 'student_id': student.id},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)
        self.assertIn(parent, student.meal_account.guardians.all())

    def test_linked_parent_can_view_real_childs_balance(self):
        # Regression: parent balance/history used to resolve to "the
        # first student in the school" — a different child entirely.
        # Now it must resolve to the actual linked child.
        other_student = create_user(
            self.school, 'student', 'Other Kid', 'otherkid@test.com')
        MealAccount.objects.create(student=other_student, balance_cents=999999)

        my_student = create_user(self.school, 'student', 'My Kid', 'mykid@test.com')
        my_account = MealAccount.objects.create(student=my_student, balance_cents=7500)
        parent = create_user(self.school, 'parent', 'RealParent', 'realparent@test.com')
        my_account.guardians.add(parent)

        token = get_token(self.client, 'realparent@test.com')
        res = self.client.get(
            '/api/payments/balance/', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['student_name'], 'My Kid')
        self.assertEqual(res.json()['balance_cents'], 7500)

    def test_non_admin_cannot_create_accounts(self):
        bursar = create_user(self.school, 'bursar', 'Bursar', 'linkbursar@test.com')
        token = get_token(self.client, 'linkbursar@test.com')
        res = self.client.post(
            '/api/auth/admin/students/',
            {'full_name': 'X', 'email': 'x@test.com', 'password': 'Password123!'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(res.status_code, 403)


# ════════════════════════════════════════
# MENU-BASED SERVING + OVERDRAFT
# ════════════════════════════════════════

class TestMenuServing(TestCase):
    def setUp(self):
        self.school = create_school('Menu School', 'menu@test.com')
        self.kitchen = create_user(self.school, 'kitchen', 'Kitchen', 'menukitchen@test.com')
        self.token = get_token(self.client, 'menukitchen@test.com')
        self.student = create_user(self.school, 'student', 'Eater', 'eater@test.com')
        self.meal_account = MealAccount.objects.create(
            student=self.student, balance_cents=10000)
        self.rice = MenuItem.objects.create(
            school=self.school, name='Rice', price_cents=3000)
        self.beans = MenuItem.objects.create(
            school=self.school, name='Beans', price_cents=3000)

    def test_serve_deducts_sum_of_selected_items(self):
        res = self.client.post(
            '/api/meals/serve/',
            {'student_id': self.student.id, 'item_ids': [self.rice.id, self.beans.id]},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 201)
        self.meal_account.refresh_from_db()
        # 10000 - (3000 + 3000) = 4000
        self.assertEqual(self.meal_account.balance_cents, 4000)
        event = MealDistributionEvent.objects.get(meal_account=self.meal_account)
        self.assertEqual(event.amount_cents, 6000)
        self.assertEqual(event.items.count(), 2)
        self.assertEqual(event.recorded_by, self.kitchen)

    def test_serve_blocked_beyond_credit_limit(self):
        # balance 1000, only KES 5 overdraft approved — 6000 total exceeds it
        self.meal_account.balance_cents = 1000
        self.meal_account.credit_limit_cents = 500
        self.meal_account.save()
        res = self.client.post(
            '/api/meals/serve/',
            {'student_id': self.student.id, 'item_ids': [self.rice.id, self.beans.id]},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 402)
        self.meal_account.refresh_from_db()
        self.assertEqual(self.meal_account.balance_cents, 1000)  # unchanged

    def test_serve_allowed_within_approved_credit_limit(self):
        self.meal_account.balance_cents = 1000
        self.meal_account.credit_limit_cents = 10000  # KES 100 overdraft approved
        self.meal_account.save()
        res = self.client.post(
            '/api/meals/serve/',
            {'student_id': self.student.id, 'item_ids': [self.rice.id, self.beans.id]},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 201)
        self.meal_account.refresh_from_db()
        self.assertEqual(self.meal_account.balance_cents, -5000)  # 1000 - 6000

    def test_serve_requires_at_least_one_item(self):
        res = self.client.post(
            '/api/meals/serve/',
            {'student_id': self.student.id, 'item_ids': []},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 400)

    def test_menu_endpoint_lists_active_items(self):
        res = self.client.get(
            '/api/meals/menu/', HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)
        names = {i['name'] for i in res.json()}
        self.assertEqual(names, {'Rice', 'Beans'})


# ════════════════════════════════════════
# MEAL COMBOS (SEARCHABLE ITEM BUNDLES)
# ════════════════════════════════════════

class TestMealCombos(TestCase):
    def setUp(self):
        self.school = create_school('Combo School', 'combo@test.com')
        self.admin = create_user(self.school, 'admin', 'Admin', 'comboadmin@test.com')
        self.admin_token = get_token(self.client, 'comboadmin@test.com')
        self.kitchen = create_user(self.school, 'kitchen', 'Kitchen', 'combokitchen@test.com')
        self.kitchen_token = get_token(self.client, 'combokitchen@test.com')
        self.rice = MenuItem.objects.create(
            school=self.school, name='Rice', price_cents=3000)
        self.beans = MenuItem.objects.create(
            school=self.school, name='Beans', price_cents=3000)
        self.sukuma = MenuItem.objects.create(
            school=self.school, name='Sukuma Wiki', price_cents=1000)

    def test_admin_creates_combo(self):
        res = self.client.post(
            '/api/meals/combos/',
            {'name': 'Lunch Special', 'item_ids': [self.rice.id, self.beans.id, self.sukuma.id]},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['total_price_cents'], 7000)
        combo = MealCombo.objects.get(name='Lunch Special')
        self.assertEqual(combo.items.count(), 3)

    def test_combo_price_reflects_live_item_prices(self):
        combo = MealCombo.objects.create(school=self.school, name='Rice & Beans')
        combo.items.set([self.rice, self.beans])
        self.assertEqual(combo.total_price_cents(), 6000)

        self.rice.price_cents = 4000
        self.rice.save()
        self.assertEqual(combo.total_price_cents(), 7000)  # updated, not stale

    def test_kitchen_can_list_combos(self):
        combo = MealCombo.objects.create(school=self.school, name='Rice & Beans')
        combo.items.set([self.rice, self.beans])
        res = self.client.get(
            '/api/meals/combos/', HTTP_AUTHORIZATION=f'Bearer {self.kitchen_token}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 1)
        self.assertEqual(res.json()[0]['total_price_ksh'], 60.0)

    def test_non_admin_cannot_create_combo(self):
        res = self.client.post(
            '/api/meals/combos/',
            {'name': 'X', 'item_ids': [self.rice.id]},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.kitchen_token}')
        self.assertEqual(res.status_code, 403)

    def test_admin_can_edit_combo_items(self):
        combo = MealCombo.objects.create(school=self.school, name='Rice & Beans')
        combo.items.set([self.rice, self.beans])
        res = self.client.patch(
            f'/api/meals/combos/{combo.id}/',
            {'item_ids': [self.rice.id, self.sukuma.id]},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        self.assertEqual(res.status_code, 200)
        combo.refresh_from_db()
        self.assertEqual(set(combo.items.values_list('id', flat=True)),
                          {self.rice.id, self.sukuma.id})

    def test_admin_can_deactivate_combo(self):
        combo = MealCombo.objects.create(school=self.school, name='Rice & Beans')
        combo.items.set([self.rice, self.beans])
        res = self.client.delete(
            f'/api/meals/combos/{combo.id}/',
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        self.assertEqual(res.status_code, 200)
        combo.refresh_from_db()
        self.assertFalse(combo.is_active)
        # deactivated combos no longer show up for kitchen staff
        res = self.client.get(
            '/api/meals/combos/', HTTP_AUTHORIZATION=f'Bearer {self.kitchen_token}')
        self.assertEqual(res.json(), [])


# ════════════════════════════════════════
# CREDIT REQUESTS (OVERDRAFT APPROVAL)
# ════════════════════════════════════════

class TestCreditRequests(TestCase):
    def setUp(self):
        self.school = create_school('Credit School', 'credit@test.com')
        self.admin = create_user(self.school, 'admin', 'Admin', 'creditadmin@test.com')
        self.admin_token = get_token(self.client, 'creditadmin@test.com')
        self.student = create_user(self.school, 'student', 'Kid', 'creditkid@test.com')
        self.meal_account = MealAccount.objects.create(
            student=self.student, balance_cents=0)
        self.parent = create_user(self.school, 'parent', 'Parent', 'creditparent@test.com')
        self.meal_account.guardians.add(self.parent)
        self.parent_token = get_token(self.client, 'creditparent@test.com')

    def test_parent_applies_for_credit(self):
        res = self.client.post(
            '/api/payments/credit-requests/',
            {'requested_amount_cents': 20000, 'reason': 'Tight month'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.parent_token}')
        self.assertEqual(res.status_code, 201)
        self.assertTrue(
            CreditRequest.objects.filter(meal_account=self.meal_account).exists())

    def test_approval_raises_credit_limit_not_balance(self):
        req = CreditRequest.objects.create(
            meal_account=self.meal_account, requested_by=self.parent,
            requested_amount_cents=20000)
        res = self.client.post(
            f'/api/payments/credit-requests/{req.id}/review/',
            {'action': 'approved', 'review_notes': 'ok'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        self.assertEqual(res.status_code, 200)
        self.meal_account.refresh_from_db()
        self.assertEqual(self.meal_account.credit_limit_cents, 20000)
        self.assertEqual(self.meal_account.balance_cents, 0)  # unchanged

    def test_rejection_does_not_change_credit_limit(self):
        req = CreditRequest.objects.create(
            meal_account=self.meal_account, requested_by=self.parent,
            requested_amount_cents=20000)
        res = self.client.post(
            f'/api/payments/credit-requests/{req.id}/review/',
            {'action': 'rejected', 'review_notes': 'no'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        self.assertEqual(res.status_code, 200)
        self.meal_account.refresh_from_db()
        self.assertEqual(self.meal_account.credit_limit_cents, 0)

    def test_double_review_returns_409(self):
        req = CreditRequest.objects.create(
            meal_account=self.meal_account, requested_by=self.parent,
            requested_amount_cents=20000, status='approved')
        res = self.client.post(
            f'/api/payments/credit-requests/{req.id}/review/',
            {'action': 'approved'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        self.assertEqual(res.status_code, 409)

    def test_non_parent_cannot_apply(self):
        res = self.client.post(
            '/api/payments/credit-requests/',
            {'requested_amount_cents': 20000},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        self.assertEqual(res.status_code, 403)

    def test_bursar_can_view_queue_but_not_review(self):
        # Bursars need visibility into credit requests for financial
        # oversight, but only an admin may actually approve/reject one.
        bursar = create_user(self.school, 'bursar', 'Bursar', 'creditbursar@test.com')
        bursar_token = get_token(self.client, 'creditbursar@test.com')
        req = CreditRequest.objects.create(
            meal_account=self.meal_account, requested_by=self.parent,
            requested_amount_cents=20000)

        res = self.client.get(
            '/api/payments/credit-requests/queue/',
            HTTP_AUTHORIZATION=f'Bearer {bursar_token}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['total'], 1)

        res = self.client.post(
            f'/api/payments/credit-requests/{req.id}/review/',
            {'action': 'approved'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {bursar_token}')
        self.assertEqual(res.status_code, 403)


# ════════════════════════════════════════
# SUPPORT ISSUES
# ════════════════════════════════════════

class TestSupportIssues(TestCase):
    def setUp(self):
        self.school = create_school('Issue School', 'issue@test.com')
        self.admin = create_user(self.school, 'admin', 'Admin', 'issueadmin@test.com')
        self.admin_token = get_token(self.client, 'issueadmin@test.com')
        self.parent = create_user(self.school, 'parent', 'Parent', 'issueparent@test.com')
        self.parent_token = get_token(self.client, 'issueparent@test.com')

    def test_parent_raises_issue(self):
        res = self.client.post(
            '/api/support/issues/',
            {'category': 'balance', 'subject': 'Wrong balance',
             'description': 'My balance looks wrong.'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.parent_token}')
        self.assertEqual(res.status_code, 201)
        self.assertTrue(
            SupportIssue.objects.filter(raised_by=self.parent).exists())

    def test_issue_auto_links_to_parents_child_when_not_specified(self):
        # The mobile app doesn't ask which child an issue concerns — the
        # backend should default to the parent's linked child (like
        # balance/history/credit-requests already do) so the admin queue
        # can show which student it's about.
        student = create_user(self.school, 'student', 'Kid', 'issuekid@test.com')
        account = MealAccount.objects.create(student=student, balance_cents=0)
        account.guardians.add(self.parent)

        res = self.client.post(
            '/api/support/issues/',
            {'category': 'meal_quality', 'subject': 'Cold food',
             'description': 'Lunch was cold today.'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.parent_token}')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['issue']['student_name'], 'Kid')

        issue = SupportIssue.objects.get(raised_by=self.parent)
        self.assertEqual(issue.meal_account, account)

    def test_admin_sees_issue_in_queue_and_resolves(self):
        issue = SupportIssue.objects.create(
            raised_by=self.parent, subject='Test', description='Test issue')
        res = self.client.get(
            '/api/support/issues/queue/',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['total'], 1)

        res = self.client.post(
            f'/api/support/issues/{issue.id}/resolve/',
            {'status': 'resolved', 'resolution_notes': 'Fixed'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        self.assertEqual(res.status_code, 200)
        issue.refresh_from_db()
        self.assertEqual(issue.status, 'resolved')
        self.assertIsNotNone(issue.resolved_at)

    def test_non_admin_cannot_access_queue(self):
        res = self.client.get(
            '/api/support/issues/queue/',
            HTTP_AUTHORIZATION=f'Bearer {self.parent_token}')
        self.assertEqual(res.status_code, 403)
