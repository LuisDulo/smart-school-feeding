"""
Seeds the Super Admin demo environment: the Webmasters Kenya organisation
record, a superadmin user, and two additional schools (Westlands Academy,
Karen Junior School) each with staff, students, meal history and payment
history, so the Super Admin dashboard has more than one school to show.

Idempotent — safe to re-run; uses get_or_create for accounts/schools and
skips a school's history seeding if it already has distribution events.
"""
import random
import bcrypt
from datetime import date, timedelta, datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from meals.models import (
    School, User, MealAccount, PaymentTransaction,
    MealDistributionEvent, AnomalyFlag
)


def make_hashed(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


FIRST_NAMES = ['Ali', 'Beth', 'Chris', 'Diana', 'Eric', 'Fiona', 'George',
               'Helen', 'Ivan', 'Jane', 'Ken', 'Lisa', 'Mike', 'Nina', 'Oscar',
               'Paula', 'Quinn', 'Rita', 'Steve', 'Tina', 'Uma', 'Vince',
               'Wendy', 'Xander', 'Yara', 'Zack', 'Amara', 'Brian', 'Clara', 'Dave']
LAST_NAMES = ['Kamau', 'Otieno', 'Wanjiku', 'Mwangi', 'Njoroge', 'Odhiambo',
              'Kiptoo', 'Mutua', 'Achieng', 'Kariuki']


class Command(BaseCommand):
    help = 'Seeds Webmasters Kenya org, a superadmin user, and two extra demo schools.'

    def handle(self, *args, **options):
        wk, _ = School.objects.get_or_create(
            name='Webmasters Kenya',
            defaults={'county': 'Nairobi',
                      'contact_email': 'admin@webmasterskenya.co.ke'}
        )
        self.stdout.write(f'Organisation: {wk.name} (id={wk.id})')

        hashed = make_hashed('SuperAdmin123!')
        sa, created = User.objects.get_or_create(
            email='superadmin@webmasterskenya.co.ke',
            defaults={
                'school': wk, 'role': 'superadmin',
                'full_name': 'Webmasters Admin',
                'hashed_password': hashed
            }
        )
        self.stdout.write(f'Superadmin: {sa.email} (created={created})')

        s2, _ = School.objects.get_or_create(
            name='Westlands Academy',
            defaults={'county': 'Nairobi',
                      'contact_email': 'admin@westlandsacademy.ac.ke'}
        )
        s3, _ = School.objects.get_or_create(
            name='Karen Junior School',
            defaults={'county': 'Nairobi',
                      'contact_email': 'admin@karenjunior.ac.ke'}
        )
        self.stdout.write(f'Test schools: {s2.name}, {s3.name}')

        self.seed_school(s2, 'westlands', 25)
        self.seed_school(s3, 'karen', 20)
        self.stdout.write(self.style.SUCCESS('All schools seeded.'))

    def seed_school(self, school, prefix, student_count=30):
        self.stdout.write(f'Seeding {school.name}...')

        kitchen, _ = User.objects.get_or_create(
            email=f'kitchen@{prefix}.ac.ke',
            defaults={
                'school': school, 'role': 'kitchen',
                'full_name': f'Kitchen {prefix}',
                'hashed_password': make_hashed('Kitchen123!')
            }
        )
        User.objects.get_or_create(
            email=f'admin@{prefix}.ac.ke',
            defaults={
                'school': school, 'role': 'admin',
                'full_name': f'Admin {prefix}',
                'hashed_password': make_hashed('Admin123!')
            }
        )
        User.objects.get_or_create(
            email=f'bursar@{prefix}.ac.ke',
            defaults={
                'school': school, 'role': 'bursar',
                'full_name': f'Bursar {prefix}',
                'hashed_password': make_hashed('Bursar123!')
            }
        )

        students = []
        for i in range(student_count):
            email = f'student{i+1:02d}@{prefix}.ac.ke'
            student, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    'school': school, 'role': 'student',
                    'full_name': f'{FIRST_NAMES[i % len(FIRST_NAMES)]} {random.choice(LAST_NAMES)}',
                    'hashed_password': make_hashed('Student123!')
                }
            )
            meal_account, _ = MealAccount.objects.get_or_create(
                student=student,
                defaults={'balance_cents': random.randint(5000, 150000)}
            )
            students.append((student, meal_account))

        if MealDistributionEvent.objects.filter(
                meal_account__student__school=school).exists():
            self.stdout.write(
                f'  {school.name}: history already seeded, skipping.')
            return

        # NOTE: created_at on both PaymentTransaction and
        # MealDistributionEvent is auto_now_add=True, so Django silently
        # ignores any created_at=... passed to .objects.create() — it
        # always stamps "now". To actually backdate these (needed for the
        # weekly/14-day trend charts to show a realistic spread), create
        # the row first, then overwrite its created_at with a raw
        # .update(), which bypasses auto_now_add since it doesn't go
        # through save().
        today = date.today()
        for i in range(20):
            d = today - timedelta(days=i)
            if d.weekday() >= 5:
                continue
            num_eating = int(len(students) * random.uniform(0.75, 0.92))
            for student, meal_account in random.sample(students, num_eating):
                event, created = MealDistributionEvent.objects.get_or_create(
                    meal_account=meal_account,
                    meal_date=d,
                    defaults={'recorded_by': kitchen, 'meals_served': 1}
                )
                if created:
                    backdated = timezone.make_aware(
                        datetime.combine(d, datetime.min.time().replace(
                            hour=12, minute=random.randint(0, 59)
                        ))
                    )
                    MealDistributionEvent.objects.filter(
                        pk=event.pk).update(created_at=backdated)

        for student, meal_account in students:
            for _ in range(random.randint(3, 8)):
                d = today - timedelta(days=random.randint(1, 30))
                amount = random.choice([10000, 20000, 30000, 50000])
                tx = PaymentTransaction.objects.create(
                    meal_account=meal_account,
                    amount_cents=amount,
                    mpesa_reference=f'QK{random.randint(1000000, 9999999)}',
                    status='confirmed',
                    callback_payload={'synthetic': True},
                )
                backdated = timezone.make_aware(
                    datetime.combine(d, datetime.min.time().replace(
                        hour=random.randint(8, 17),
                        minute=random.randint(0, 59)
                    ))
                )
                PaymentTransaction.objects.filter(
                    pk=tx.pk).update(created_at=backdated)
                meal_account.balance_cents += amount
                meal_account.save()

        for _ in range(3):
            student, meal_account = random.choice(students)
            tx = PaymentTransaction.objects.create(
                meal_account=meal_account,
                amount_cents=random.choice([500000, 750000]),
                mpesa_reference=f'ANOM{random.randint(10000, 99999)}',
                status='confirmed',
                callback_payload={'anomalous': True},
            )
            AnomalyFlag.objects.create(
                transaction=tx,
                anomaly_score=round(random.uniform(0.70, 0.92), 3),
                reviewed=False
            )

        self.stdout.write(f'  {school.name}: {student_count} students seeded.')
