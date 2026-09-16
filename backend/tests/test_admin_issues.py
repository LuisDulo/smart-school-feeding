from django.test import TestCase
from meals.models import School, User, AdminIssue
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


class TestAdminIssues(TestCase):
    def setUp(self):
        self.wk = School.objects.create(
            name='Webmasters Kenya', county='Nairobi',
            contact_email='wk@test.com')
        self.superadmin = create_user(
            self.wk, 'superadmin', 'Super Admin', 'sa@wk.test')
        self.sa_token = get_token(self.client, 'sa@wk.test')

        self.school = create_school('Report School', 'reportschool@test.com')
        self.admin = create_user(
            self.school, 'admin', 'School Admin', 'admin@reportschool.test')
        self.admin_token = get_token(self.client, 'admin@reportschool.test')

    def test_admin_raises_report(self):
        res = self.client.post(
            '/api/support/admin-issues/',
            {'category': 'technical', 'subject': 'Dashboard crashes',
             'description': 'The Serve Meals page crashes on load.'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        self.assertEqual(res.status_code, 201)
        self.assertTrue(
            AdminIssue.objects.filter(raised_by=self.admin).exists())
        self.assertEqual(res.json()['issue']['school_name'], 'Report School')

    def test_non_admin_roles_cannot_raise_report(self):
        for role in ['parent', 'student', 'kitchen', 'bursar']:
            user = create_user(
                self.school, role, f'{role} user', f'{role}@reportschool.test')
            token = get_token(self.client, f'{role}@reportschool.test')
            res = self.client.post(
                '/api/support/admin-issues/',
                {'category': 'other', 'subject': 'X', 'description': 'Y'},
                content_type='application/json',
                HTTP_AUTHORIZATION=f'Bearer {token}')
            self.assertEqual(res.status_code, 403, f'{role} should be forbidden')

    def test_admin_sees_own_reports(self):
        AdminIssue.objects.create(
            raised_by=self.admin, subject='Issue 1', description='desc')
        other_school = create_school('Other School', 'other@test.com')
        other_admin = create_user(
            other_school, 'admin', 'Other Admin', 'other-admin@test.com')
        AdminIssue.objects.create(
            raised_by=other_admin, subject='Issue 2', description='desc')

        res = self.client.get(
            '/api/support/admin-issues/',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        self.assertEqual(res.status_code, 200)
        subjects = [i['subject'] for i in res.json()]
        self.assertEqual(subjects, ['Issue 1'])

    def test_superadmin_sees_reports_from_all_schools(self):
        other_school = create_school('Other School', 'other2@test.com')
        other_admin = create_user(
            other_school, 'admin', 'Other Admin', 'other-admin2@test.com')
        AdminIssue.objects.create(
            raised_by=self.admin, subject='Issue from Report School', description='d')
        AdminIssue.objects.create(
            raised_by=other_admin, subject='Issue from Other School', description='d')

        res = self.client.get(
            '/api/support/admin-issues/queue/',
            HTTP_AUTHORIZATION=f'Bearer {self.sa_token}')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['total'], 2)
        schools = {i['school_name'] for i in data['issues']}
        self.assertEqual(schools, {'Report School', 'Other School'})

    def test_school_admin_cannot_access_queue(self):
        res = self.client.get(
            '/api/support/admin-issues/queue/',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        self.assertEqual(res.status_code, 403)

    def test_superadmin_resolves_report(self):
        issue = AdminIssue.objects.create(
            raised_by=self.admin, subject='Fix this', description='d')
        res = self.client.post(
            f'/api/support/admin-issues/{issue.id}/resolve/',
            {'status': 'resolved', 'resolution_notes': 'Fixed in v1.2'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.sa_token}')
        self.assertEqual(res.status_code, 200)
        issue.refresh_from_db()
        self.assertEqual(issue.status, 'resolved')
        self.assertEqual(issue.resolved_by, self.superadmin)
        self.assertIsNotNone(issue.resolved_at)

    def test_school_admin_cannot_resolve_report(self):
        issue = AdminIssue.objects.create(
            raised_by=self.admin, subject='Fix this', description='d')
        res = self.client.post(
            f'/api/support/admin-issues/{issue.id}/resolve/',
            {'status': 'resolved'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        self.assertEqual(res.status_code, 403)

    def test_double_resolve_returns_409(self):
        issue = AdminIssue.objects.create(
            raised_by=self.admin, subject='Fix this', description='d',
            status='resolved')
        res = self.client.post(
            f'/api/support/admin-issues/{issue.id}/resolve/',
            {'status': 'resolved'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.sa_token}')
        self.assertEqual(res.status_code, 409)

    def test_queue_filters_by_status(self):
        AdminIssue.objects.create(
            raised_by=self.admin, subject='Open one', description='d', status='open')
        AdminIssue.objects.create(
            raised_by=self.admin, subject='Resolved one', description='d',
            status='resolved')
        res = self.client.get(
            '/api/support/admin-issues/queue/?status=open',
            HTTP_AUTHORIZATION=f'Bearer {self.sa_token}')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['issues'][0]['subject'], 'Open one')
