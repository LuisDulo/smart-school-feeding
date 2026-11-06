import random
from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Avg
from django.utils import timezone

from anomalies import meal_detection
from anomalies.views import score_and_flag_transaction
from meals.models import (BlockedServeAttempt, MealAccount,
                          MealAnomalyFlag, MealDistributionEvent,
                          PaymentTransaction, School, User)

SIM_PREFIX = 'SIMULATED-'


class Command(BaseCommand):
    help = ('DEMO TOOL. Creates a handful of realistic unusual cases (a huge '
            'top-up, a burst of top-ups, a 3 a.m. payment, night / weekend / '
            'very expensive meals, repeated blocked serve attempts) and runs '
            'them through the real detectors so they appear on the Anomaly '
            'Flags page. Balances are not changed. Re-running replaces the '
            'previous demo rows; --cleanup removes them.')

    def add_arguments(self, parser):
        parser.add_argument('--school', type=int, default=None,
                            help='School id (default: the first school that is not the HQ).')
        parser.add_argument('--cleanup', action='store_true',
                            help='Remove all simulated rows and stop.')

    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        removed = self.cleanup()
        self.stdout.write(
            f"Removed previous demo rows: {removed['transactions']} top-up(s), "
            f"{removed['meals']} meal(s), {removed['flags']} flag(s), "
            f"{removed['attempts']} blocked attempt(s).")
        if options['cleanup']:
            return

        school = self.pick_school(options['school'])
        kitchen = User.objects.filter(school=school, role='kitchen').first()
        if kitchen is None:
            raise CommandError(f'{school.name} has no kitchen account to attribute demo meals to.')
        accounts = list(MealAccount.objects.filter(student__school=school)
                        .select_related('student').order_by('id'))
        if len(accounts) < 12:
            raise CommandError(f'{school.name} needs at least 12 students for the demo.')
        rng = random.Random(2026)
        picks = rng.sample(accounts, 12)
        today = timezone.localdate()

        self.stdout.write(f'\nCreating demo anomalies at {school.name}:')
        self.simulate_payments(picks[0:3], today)
        flags_before = set(MealAnomalyFlag.objects.values_list('id', flat=True))
        self.simulate_meals(picks[3:12], kitchen, today)
        new_flags = MealAnomalyFlag.objects.exclude(id__in=flags_before)
        new_flags.update(is_demo=True)
        self.stdout.write(self.style.SUCCESS(
            '\nDone. Open the Anomaly Flags page (Payments and Meal Serving tabs). '
            'Remove these demo rows afterwards with: '
            'python manage.py simulate_anomalies --cleanup'))

    # ------------------------------------------------------------------
    def pick_school(self, school_id):
        if school_id is not None:
            try:
                return School.objects.get(id=school_id)
            except School.DoesNotExist:
                raise CommandError(f'No school with id {school_id}.')
        school = School.objects.exclude(name='Webmasters Kenya').order_by('id').first()
        if school is None:
            raise CommandError('No school found.')
        return school

    def cleanup(self):
        txs = PaymentTransaction.objects.filter(mpesa_reference__startswith=SIM_PREFIX)
        n_tx = txs.count()
        txs.delete()  # cascades to the top-up AnomalyFlag rows

        demo_flags = MealAnomalyFlag.objects.filter(is_demo=True)
        n_flags = demo_flags.count()
        event_ids = list(demo_flags.exclude(meal_event=None)
                         .values_list('meal_event_id', flat=True))
        MealDistributionEvent.objects.filter(id__in=event_ids).delete()
        demo_flags.delete()
        attempts = BlockedServeAttempt.objects.filter(reason='simulated')
        n_attempts = attempts.count()
        attempts.delete()
        return {'transactions': n_tx, 'meals': len(event_ids),
                'flags': n_flags, 'attempts': n_attempts}

    @staticmethod
    def at(day, hour, minute=0):
        return timezone.make_aware(datetime.combine(day, time(hour, minute)))

    # ------------------------------------------------------------------
    def make_topup(self, account, amount_cents, when, tag):
        tx = PaymentTransaction.objects.create(
            meal_account=account, amount_cents=amount_cents, status='confirmed',
            mpesa_reference=f'{SIM_PREFIX}{tag}',
            callback_payload={'simulated': True})
        PaymentTransaction.objects.filter(pk=tx.pk).update(created_at=when)
        tx.refresh_from_db()
        return tx

    def report_tx(self, label, tx):
        flag, score = score_and_flag_transaction(tx)
        if score is None:
            self.stdout.write(f'  - {label}: top-up anomaly model not loaded, not scored')
        elif flag:
            self.stdout.write(self.style.SUCCESS(
                f'  - {label}: FLAGGED (score {score})'))
        else:
            self.stdout.write(self.style.WARNING(
                f'  - {label}: scored {score} but the model did not flag it'))

    def simulate_payments(self, accounts, today):
        big, burst, night = accounts
        self.stdout.write(' Top-ups:')
        usual = PaymentTransaction.objects.filter(
            meal_account=big, status='confirmed').aggregate(a=Avg('amount_cents'))['a'] or 50000
        tx = self.make_topup(big, int(max(usual * 15, 2_500_000)),
                             self.at(today, 10, 5), 'large')
        self.report_tx(f'{big.student.full_name}: very large top-up', tx)

        for i in range(4):
            tx = self.make_topup(burst, 50000, self.at(today, 14, 10 + 2 * i), f'burst{i}')
        self.report_tx(f'{burst.student.full_name}: 4 top-ups in 6 minutes (last one scored)', tx)

        tx = self.make_topup(night, 1_200_000, self.at(today, 3, 12), 'night')
        self.report_tx(f'{night.student.full_name}: top-up of KES 12,000 at 03:12', tx)

    # ------------------------------------------------------------------
    def make_meal(self, account, kitchen, amount_cents, meal_day, hour, minute):
        event = MealDistributionEvent.objects.create(
            meal_account=account, recorded_by=kitchen,
            meal_date=meal_day, meals_served=1, amount_cents=amount_cents)
        MealDistributionEvent.objects.filter(pk=event.pk).update(
            created_at=self.at(meal_day, hour, minute))
        event.refresh_from_db()
        return event

    def report_meal(self, label, event):
        flag = meal_detection.flag_meal_event(event)
        if flag:
            flag.is_demo = True
            flag.save(update_fields=['is_demo'])
            self.stdout.write(self.style.SUCCESS(
                f'  - {label}: FLAGGED (score {flag.anomaly_score}) - '
                f'{"; ".join(flag.reasons)}'))
        else:
            self.stdout.write(self.style.WARNING(f'  - {label}: not flagged'))

    def simulate_meals(self, accounts, kitchen, today):
        # The "costly meal" case compares with the student's usual cost, so it
        # needs someone who already has meal history.
        history = lambda a: MealDistributionEvent.objects.filter(  # noqa: E731
            meal_account=a).count()
        costly = max(accounts, key=history)
        rest = [a for a in accounts if a.id != costly.id]
        night, weekend, repeat = rest[0:3]
        staff_students = rest[3:8]
        self.stdout.write(' Meals:')

        usual = lambda a: int(MealDistributionEvent.objects.filter(  # noqa: E731
            meal_account=a).aggregate(v=Avg('amount_cents'))['v'] or 5000)

        self.report_meal(f'{night.student.full_name}: meal at 02:40',
                         self.make_meal(night, kitchen, usual(night), today, 2, 40))

        saturday = today - timedelta(days=(today.weekday() - 5) % 7 or 7)
        self.report_meal(f'{weekend.student.full_name}: meal on Saturday {saturday}',
                         self.make_meal(weekend, kitchen, usual(weekend), saturday, 10, 15))

        amount = max(30000, usual(costly) * 5)
        self.report_meal(f'{costly.student.full_name}: meal costing KES {amount // 100}',
                         self.make_meal(costly, kitchen, amount, today, 12, 20))

        for _ in range(3):
            meal_detection.record_blocked_attempt(
                repeat, kitchen, reason='simulated', today=today)
        self.stdout.write(self.style.SUCCESS(
            f'  - {repeat.student.full_name}: refused 3 times at the daily limit (flag raised)'))

        for account in staff_students:
            meal_detection.record_blocked_attempt(
                account, kitchen, reason='simulated', today=today)
        self.stdout.write(self.style.SUCCESS(
            f'  - {kitchen.full_name}: blocked {3 + len(staff_students)} times today '
            f'(staff flag raised)'))
