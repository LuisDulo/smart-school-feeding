import random
from datetime import timedelta, datetime, time as dtime

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from meals.models import (
    School, User, MealAccount, MenuItem, MealDistributionEvent, PaymentTransaction,
)


class Command(BaseCommand):
    help = ('Backfills meal-serving and top-up activity from the day after the '
            'last existing record through today, so "today" stats, 7/14-day '
            'charts, and network trend lines on the dashboards are populated '
            'instead of showing zeros.')

    def handle(self, *args, **options):
        random.seed(7)
        today = timezone.localdate()
        last_event = MealDistributionEvent.objects.order_by('-meal_date').first()
        start = (last_event.meal_date + timedelta(days=1)) if last_event else today - timedelta(days=14)
        if start > today:
            self.stdout.write('Already up to date, nothing to backfill.')
            return

        days = [start + timedelta(days=i) for i in range((today - start).days + 1)]
        self.stdout.write(f'Backfilling {len(days)} day(s): {start} -> {today}')

        schools = School.objects.exclude(name='Webmasters Kenya')
        meals_created = 0
        payments_created = 0

        with transaction.atomic():
            for school in schools:
                kitchen = User.objects.filter(school=school, role='kitchen').first()
                items = list(MenuItem.objects.filter(school=school, is_active=True))
                accounts = list(MealAccount.objects.filter(student__school=school)
                                 .select_related('student'))
                if not accounts:
                    continue

                for day in days:
                    is_weekend = day.weekday() >= 5
                    for account in accounts:
                        if is_weekend:
                            continue
                        # ~87% daily attendance, matching the synthetic
                        # training-data generator's base attendance rate.
                        if random.random() > 0.87:
                            continue

                        if items:
                            chosen = random.sample(items, k=min(len(items), random.choice([2, 3])))
                            amount_cents = sum(i.price_cents for i in chosen)
                        else:
                            chosen = []
                            amount_cents = random.choice([3000, 4000, 5000, 6000, 7000])

                        if account.balance_cents - amount_cents < -account.credit_limit_cents:
                            continue  # would breach approved overdraft; skip like RecordMealView would

                        served_hour = random.choice([7, 8, 12, 13])
                        served_at = timezone.make_aware(
                            datetime.combine(day, dtime(served_hour, random.randint(0, 59))))

                        event = MealDistributionEvent.objects.create(
                            meal_account=account,
                            recorded_by=kitchen,
                            amount_cents=amount_cents,
                            meal_date=day,
                            meals_served=1,
                        )
                        if chosen:
                            event.items.set(chosen)
                        MealDistributionEvent.objects.filter(pk=event.pk).update(created_at=served_at)

                        account.balance_cents -= amount_cents
                        meals_created += 1

                        # ~12% chance a top-up happens same day, usually
                        # triggered by a low/depleting balance.
                        if random.random() < 0.12 or account.balance_cents < 20000:
                            topup = random.choice([20000, 30000, 50000, 70000, 100000])
                            pay_hour = random.choice([6, 7, 17, 18, 19])
                            pay_at = timezone.make_aware(
                                datetime.combine(day, dtime(pay_hour, random.randint(0, 59))))
                            tx = PaymentTransaction.objects.create(
                                meal_account=account,
                                amount_cents=topup,
                                mpesa_reference=f'RCV{random.randint(100000, 999999)}',
                                status='confirmed',
                            )
                            PaymentTransaction.objects.filter(pk=tx.pk).update(created_at=pay_at)
                            account.balance_cents += topup
                            payments_created += 1

                        account.save(update_fields=['balance_cents'])

        self.stdout.write(self.style.SUCCESS(
            f'Created {meals_created} meal events and {payments_created} '
            f'payments across {schools.count()} schools, {start} -> {today}.'
        ))
