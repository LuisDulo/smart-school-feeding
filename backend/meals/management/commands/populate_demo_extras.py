import random
from datetime import timedelta, datetime, time as dtime

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from meals.models import (
    School, User, MealAccount, MealDistributionEvent, PaymentTransaction,
    CreditRequest, SupportIssue, AdminIssue, DemandForecast,
)


def aware(day, hour, minute=0):
    return timezone.make_aware(datetime.combine(day, dtime(hour, minute)))


class Command(BaseCommand):
    help = ('Populates the currently-empty demo screens (Credit Requests, '
            'Support Issues, Platform/School Reports), creates a realistic '
            'spread of at-risk / low-balance students so the Balance Risk '
            'classifier and the network balance-distribution chart have '
            'real data, and backfills forecast-accuracy history for the '
            'two schools that never had forecasts generated.')

    def handle(self, *args, **options):
        random.seed(11)
        today = timezone.localdate()

        with transaction.atomic():
            self.make_credit_requests()
            self.make_support_issues()
            self.make_admin_issues()
            self.make_at_risk_students()
            self.make_balance_diversity()
            self.make_forecast_history(today)

        self.stdout.write(self.style.SUCCESS('Demo data population complete.'))

    # ------------------------------------------------------------------
    def strathmore(self):
        return School.objects.get(name='Strathmore Primary School')

    def guardian_accounts(self, school, n):
        accounts = list(MealAccount.objects.filter(
            student__school=school).exclude(guardians=None).distinct())
        random.shuffle(accounts)
        return accounts[:n]

    # ------------------------------------------------------------------
    def make_credit_requests(self):
        school = self.strathmore()
        admin = User.objects.filter(school=school, role='admin').first()
        accounts = self.guardian_accounts(school, 6)
        if not accounts:
            return

        reasons = [
            'Balance ran low before end of month, need a top-up buffer for this week.',
            "Haven't been paid yet this week, please allow a small credit line.",
            'Unexpected school trip cost, need extra spending room for lunch.',
            'Salary delayed, requesting temporary credit until Friday.',
            'Topping up tomorrow morning, need him to eat today.',
            'Requesting a buffer during the holiday transition period.',
        ]
        plans = [
            ('pending', None), ('pending', None), ('pending', None),
            ('approved', 'Approved - good payment history.'),
            ('approved', 'Approved - one-time buffer.'),
            ('rejected', 'Declined - existing credit already outstanding.'),
        ]

        created = 0
        for account, (status, notes), reason in zip(accounts, plans, reasons):
            if CreditRequest.objects.filter(meal_account=account, reason=reason).exists():
                continue
            guardian = account.guardians.first()
            amount = random.choice([30000, 50000, 70000, 100000])
            when = timezone.now() - timedelta(days=random.randint(1, 8))
            cr = CreditRequest.objects.create(
                meal_account=account,
                requested_by=guardian,
                requested_amount_cents=amount,
                reason=reason,
                status=status,
            )
            CreditRequest.objects.filter(pk=cr.pk).update(created_at=when)
            if status in ('approved', 'rejected'):
                CreditRequest.objects.filter(pk=cr.pk).update(
                    reviewed_by=admin, review_notes=notes,
                    reviewed_at=when + timedelta(hours=random.randint(1, 20)))
                if status == 'approved':
                    account.credit_limit_cents += amount
                    account.save(update_fields=['credit_limit_cents'])
            created += 1
        self.stdout.write(f'Credit requests created: {created}')

    # ------------------------------------------------------------------
    def make_support_issues(self):
        school = self.strathmore()
        admin = User.objects.filter(school=school, role='admin').first()
        accounts = self.guardian_accounts(school, 6)
        if not accounts:
            return

        issues = [
            ('balance', 'Balance did not update after M-Pesa payment',
             "I topped up KES 500 this morning but the app still shows the old balance. "
             "M-Pesa confirmation SMS received.", 'resolved',
             'Confirmed the payment and manually reconciled the balance. Fixed.'),
            ('meal_quality', 'Rice was undercooked on Tuesday',
             'My daughter mentioned the rice served on Tuesday was undercooked. '
             'Please check with the kitchen.', 'in_progress',
             'Raised with kitchen staff, monitoring the next few days.'),
            ('technical', 'Cannot see QR code on my phone',
             "The QR code screen shows a blank white box instead of the code.", 'open', ''),
            ('other', 'Requesting balance transfer between siblings',
             'Can I move KES 200 from my son\'s account to my daughter\'s account?', 'open', ''),
            ('balance', 'Wrong amount deducted for lunch',
             'I was charged KES 85 but the meal combo should be KES 65.', 'resolved',
             'Verified with kitchen log - correct combo included an extra side. No error.'),
            ('technical', 'App keeps logging me out',
             'I have to sign in again every time I open the app on my phone.', 'in_progress',
             'Escalated to the platform team, likely a token refresh issue.'),
        ]

        created = 0
        for account, (category, subject, desc, status, notes) in zip(accounts, issues):
            if SupportIssue.objects.filter(meal_account=account, subject=subject).exists():
                continue
            guardian = account.guardians.first()
            when = timezone.now() - timedelta(days=random.randint(1, 10))
            issue = SupportIssue.objects.create(
                raised_by=guardian,
                meal_account=account,
                category=category,
                subject=subject,
                description=desc,
                status=status,
            )
            SupportIssue.objects.filter(pk=issue.pk).update(created_at=when)
            if status in ('in_progress', 'resolved'):
                SupportIssue.objects.filter(pk=issue.pk).update(
                    resolved_by=admin if status == 'resolved' else None,
                    resolution_notes=notes,
                    resolved_at=when + timedelta(hours=random.randint(2, 40)) if status == 'resolved' else None,
                )
            created += 1
        self.stdout.write(f'Support issues created: {created}')

    # ------------------------------------------------------------------
    def make_admin_issues(self):
        entries = [
            ('Strathmore Primary School', 'technical', 'CSV export missing last day of data',
             'The Meal Distribution CSV export seems to cut off one day early.', 'open', None),
            ('Strathmore Primary School', 'feature_request', 'Bulk QR card reprint',
             'Could we get an option to reprint QR cards for a whole class at once?', 'in_progress',
             'Logged as a feature request for the next sprint.'),
            ('Westlands Academy', 'billing', 'Invoice for last term',
             'We have not received last term\'s platform invoice yet.', 'resolved',
             'Invoice resent to school finance email on request.'),
            ('Karen Junior School', 'data', 'Duplicate student record',
             'One student appears twice in the All Students export.', 'open', None),
        ]
        created = 0
        for school_name, category, subject, desc, status, notes in entries:
            school = School.objects.filter(name=school_name).first()
            if not school:
                continue
            admin = User.objects.filter(school=school, role='admin').first()
            if not admin or AdminIssue.objects.filter(subject=subject).exists():
                continue
            when = timezone.now() - timedelta(days=random.randint(1, 12))
            issue = AdminIssue.objects.create(
                raised_by=admin, category=category, subject=subject,
                description=desc, status=status,
            )
            AdminIssue.objects.filter(pk=issue.pk).update(created_at=when)
            if status in ('in_progress', 'resolved'):
                superadmin = User.objects.filter(role='superadmin').first()
                AdminIssue.objects.filter(pk=issue.pk).update(
                    resolved_by=superadmin if status == 'resolved' else None,
                    resolution_notes=notes or '',
                    resolved_at=when + timedelta(hours=random.randint(2, 48)) if status == 'resolved' else None,
                )
            created += 1
        self.stdout.write(f'Admin issues created: {created}')

    # ------------------------------------------------------------------
    def make_at_risk_students(self):
        """Give a handful of Strathmore students a genuine 'about to run
        out' profile: low balance, no recent top-up, but still eating
        normally -- so the Random Forest risk classifier actually flags
        some of them instead of coming back empty."""
        school = self.strathmore()
        accounts = list(MealAccount.objects.filter(student__school=school)
                         .order_by('balance_cents')[:8])

        for i, account in enumerate(accounts):
            # Remove ALL top-up history so "days since last top-up" reads as
            # stale (the classifier's dominant feature is estimated days
            # remaining = balance / daily meal cost, which only drops below
            # its decision boundary once balance is very close to zero).
            PaymentTransaction.objects.filter(
                meal_account=account, status='confirmed').delete()
            target = random.choice([0, 500, 1000, 1500, 2000, 3000])  # cents (KES 0-30)
            account.balance_cents = target
            account.save(update_fields=['balance_cents'])
        self.stdout.write(f'At-risk profile applied to {len(accounts)} Strathmore students.')

    # ------------------------------------------------------------------
    def make_balance_diversity(self):
        """Spread a few students at each real school across the KES 0 /
        1-100 / 100-500 / 500-1000 brackets so the network-wide balance
        distribution pie has more than one slice."""
        for school_name in ('Westlands Academy', 'Karen Junior School'):
            school = School.objects.filter(name=school_name).first()
            if not school:
                continue
            accounts = list(MealAccount.objects.filter(student__school=school)
                             .order_by('balance_cents')[:5])
            targets = [0, 5000, 30000, 70000, 90000]  # cents: 0, 50, 300, 700, 900 KES
            for account, target in zip(accounts, targets):
                PaymentTransaction.objects.filter(
                    meal_account=account, status='confirmed',
                    created_at__date__gte=timezone.localdate() - timedelta(days=20),
                ).delete()
                account.balance_cents = target
                account.save(update_fields=['balance_cents'])
            self.stdout.write(f'Balance diversity applied at {school_name}: {len(accounts)} accounts.')

    # ------------------------------------------------------------------
    def make_forecast_history(self, today):
        """Backfill DemandForecast rows for schools that never had a
        forecast generated, so cross-school forecast-accuracy has data
        for every school instead of 'No forecasts'."""
        for school_name in ('Westlands Academy', 'Karen Junior School'):
            school = School.objects.filter(name=school_name).first()
            if not school:
                continue
            if DemandForecast.objects.filter(school=school).exists():
                continue

            created = 0
            for i in range(1, 21):
                day = today - timedelta(days=i)
                if day.weekday() >= 5:
                    continue
                actual = MealDistributionEvent.objects.filter(
                    meal_account__student__school=school, meal_date=day
                ).count()
                if actual == 0:
                    continue
                predicted = max(1, actual + random.randint(-3, 3))
                fc = DemandForecast.objects.create(
                    school=school,
                    forecast_date=day,
                    predicted_meals=predicted,
                    predicted_cost_cents=predicted * 5000,
                )
                DemandForecast.objects.filter(pk=fc.pk).update(
                    generated_at=aware(day, 6, random.randint(0, 59)))
                created += 1
            self.stdout.write(f'Forecast history backfilled for {school_name}: {created} days.')
