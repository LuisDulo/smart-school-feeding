import random
from datetime import timedelta

import bcrypt
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from meals.models import (
    School,
    User,
    MealAccount,
    PaymentTransaction,
    MealDistributionEvent,
)

STUDENT_FIRST_NAMES = [
    'Amina', 'Brian', 'Cynthia', 'David', 'Esther',
    'Felix', 'Grace', 'Hassan', 'Irene', 'James',
]
STUDENT_LAST_NAME = 'Student'

STARTING_BALANCE_CENTS = 50000  # KES 500
NUM_STUDENTS = 10
NUM_DISTRIBUTION_DAYS = 30
TRANSACTIONS_PER_STUDENT = 5
MIN_TRANSACTION_KSH = 100
MAX_TRANSACTION_KSH = 500


def make_hashed(password):
    """Hash with bcrypt — matches accounts.serializers.RegisterSerializer,
    which is what LoginView's bcrypt.checkpw() expects."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


class Command(BaseCommand):
    help = 'Seed the database with demo data for Smart School Feeding.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')

        school, _ = School.objects.get_or_create(
            contact_email='info@strathmoreprimary.ac.ke',
            defaults={
                'name': 'Strathmore Primary School',
                'county': 'Nairobi',
            },
        )
        self.stdout.write(self.style.SUCCESS(f'School: {school.name}'))

        kitchen_user, _ = User.objects.get_or_create(
            email='kitchen@strathmoreprimary.ac.ke',
            defaults={
                'school': school,
                'role': 'kitchen',
                'full_name': 'Kitchen Staff',
                'hashed_password': make_hashed('Kitchen1234!'),
            },
        )

        bursar_user, _ = User.objects.get_or_create(
            email='bursar@strathmoreprimary.ac.ke',
            defaults={
                'school': school,
                'role': 'bursar',
                'full_name': 'School Bursar',
                'hashed_password': make_hashed('Bursar1234!'),
            },
        )

        admin_user, _ = User.objects.get_or_create(
            email='schooladmin@strathmoreprimary.ac.ke',
            defaults={
                'school': school,
                'role': 'admin',
                'full_name': 'School Admin',
                'hashed_password': make_hashed('SchoolAdmin1234!'),
            },
        )

        self.stdout.write(self.style.SUCCESS(
            'Created kitchen, bursar and admin users.'
        ))

        # --- Students + meal accounts ---
        students = []
        for i, first_name in enumerate(STUDENT_FIRST_NAMES[:NUM_STUDENTS], start=1):
            student, _ = User.objects.get_or_create(
                email=f'student{i}@strathmoreprimary.ac.ke',
                defaults={
                    'school': school,
                    'role': 'student',
                    'full_name': f'{first_name} {STUDENT_LAST_NAME}{i}',
                    'hashed_password': make_hashed(f'Student{i}1234!'),
                },
            )
            students.append(student)

        meal_accounts = []
        for student in students:
            meal_account, _ = MealAccount.objects.get_or_create(
                student=student,
                defaults={'balance_cents': STARTING_BALANCE_CENTS},
            )
            meal_accounts.append(meal_account)

        self.stdout.write(self.style.SUCCESS(
            f'Created {len(students)} students and {len(meal_accounts)} meal accounts.'
        ))

        # --- 30 days of meal distribution events (school days only) ---
        today = timezone.localdate()
        school_days = []
        day_cursor = today
        while len(school_days) < NUM_DISTRIBUTION_DAYS:
            if day_cursor.weekday() < 5:  # Mon-Fri
                school_days.append(day_cursor)
            day_cursor -= timedelta(days=1)
        school_days.reverse()

        distribution_count = 0
        for meal_account in meal_accounts:
            for meal_date in school_days:
                _, created = MealDistributionEvent.objects.get_or_create(
                    meal_account=meal_account,
                    meal_date=meal_date,
                    defaults={
                        'recorded_by': kitchen_user,
                        'meals_served': 1,
                    },
                )
                if created:
                    distribution_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Created {distribution_count} meal distribution events '
            f'across {len(school_days)} school days.'
        ))

        # --- 5 confirmed payment transactions per student ---
        transaction_count = 0
        for meal_account in meal_accounts:
            for j in range(TRANSACTIONS_PER_STUDENT):
                amount_ksh = random.randint(MIN_TRANSACTION_KSH, MAX_TRANSACTION_KSH)
                PaymentTransaction.objects.create(
                    meal_account=meal_account,
                    amount_cents=amount_ksh * 100,
                    mpesa_reference=f'SEED{meal_account.student_id}{j:02d}{random.randint(1000, 9999)}',
                    status='confirmed',
                    callback_payload={'seed': True},
                )
                transaction_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Created {transaction_count} confirmed payment transactions.'
        ))

        self.stdout.write(self.style.SUCCESS('Seeding complete.'))
