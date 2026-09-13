import sys
import random
import bcrypt
from datetime import date, timedelta, datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from meals.models import (
    School, User, MealAccount, PaymentTransaction,
    MealDistributionEvent, DemandForecast, AnomalyFlag
)


def make_hashed(password):
    return bcrypt.hashpw(
        password.encode('utf-8'), bcrypt.gensalt()
    ).decode('utf-8')


def is_school_day(d):
    if d.weekday() >= 5:
        return False
    kenyan_holidays_2026 = [
        date(2026, 1, 1), date(2026, 4, 3), date(2026, 4, 6),
        date(2026, 5, 1), date(2026, 6, 1), date(2026, 10, 10),
        date(2026, 10, 20), date(2026, 12, 12),
        date(2026, 12, 25), date(2026, 12, 26),
    ]
    return d not in kenyan_holidays_2026


def get_term_week(d, term_start):
    delta = (d - term_start).days
    if delta < 0:
        return None
    week = (delta // 7) + 1
    return min(week, 13)


def is_exam_week(week_number):
    return week_number in [12, 13] if week_number else False


def get_attendance_rate(d, week_number):
    base = 0.88
    if d.weekday() == 0:
        base -= 0.05
    if d.weekday() == 4:
        base -= 0.04
    if week_number and is_exam_week(week_number):
        base -= 0.12
    if week_number == 1:
        base -= 0.08
    base += random.uniform(-0.04, 0.04)
    return max(0.60, min(0.98, base))


def backdate(model_cls, pk, dt):
    """
    PaymentTransaction.created_at and MealDistributionEvent.created_at are
    auto_now_add=True, so Django forces them to "now" on every .create()
    no matter what you pass in — the timestamp has to be corrected with a
    separate .update(), which issues a plain SQL UPDATE and bypasses
    auto_now_add entirely.
    """
    model_cls.objects.filter(pk=pk).update(created_at=dt)


class Command(BaseCommand):
    help = 'Generate 6 months of realistic synthetic training data'

    def handle(self, *args, **options):
        # Windows consoles often default to a legacy codepage (e.g. cp1252)
        # that can't encode non-ASCII characters and would crash mid-run.
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')

        self.stdout.write('Starting data generation...')
        random.seed(42)

        # Wipe any data left over from earlier sprints' seed commands —
        # otherwise student counts, attendance rates (events / enrolment)
        # and "collected today" stats get contaminated by unrelated rows
        # from a different email-numbering scheme and a different date
        # window that partially overlaps this one.
        existing = School.objects.count()
        if existing:
            self.stdout.write(
                f'Clearing {existing} existing school(s) and all related '
                'data for a clean synthetic dataset...')
            School.objects.all().delete()

        # School
        school, _ = School.objects.get_or_create(
            name='Strathmore Primary School',
            defaults={
                'county': 'Nairobi',
                'contact_email': 'admin@strathmoreprimary.ac.ke'
            }
        )
        self.stdout.write(f'School: {school.name}')

        # Staff
        kitchen, _ = User.objects.get_or_create(
            email='kitchen@strathmoreprimary.ac.ke',
            defaults={
                'school': school, 'role': 'kitchen',
                'full_name': 'Mary Wambui',
                'hashed_password': make_hashed('Kitchen123!')
            }
        )
        bursar, _ = User.objects.get_or_create(
            email='bursar@strathmoreprimary.ac.ke',
            defaults={
                'school': school, 'role': 'bursar',
                'full_name': 'James Kariuki',
                'hashed_password': make_hashed('Bursar123!')
            }
        )
        admin_user, _ = User.objects.get_or_create(
            email='admin@strathmoreprimary.ac.ke',
            defaults={
                'school': school, 'role': 'admin',
                'full_name': 'Grace Njoroge',
                'hashed_password': make_hashed('Admin123!')
            }
        )

        # 50 Students
        kenyan_first_names = [
            'Amara','Baraka','Ciku','Daudi','Esther','Fatuma','George',
            'Harriet','Ian','Joyce','Kamau','Linet','Moses','Naomi',
            'Owen','Purity','Quinter','Robert','Sharon','Timothy',
            'Usha','Victor','Wanjiku','Xavier','Yvonne','Zawadi',
            'Abel','Beatrice','Collins','Diana','Edwin','Faith',
            'Gabriel','Hellen','Isaac','Janet','Kevin','Lucy',
            'Mark','Nancy','Oliver','Priscilla','Quinton','Rachel',
            'Samuel','Tabitha','Usman','Valentine','Winnie','Zach'
        ]
        kenyan_last_names = [
            'Kamau','Wanjiku','Otieno','Mwangi','Njoroge','Odhiambo',
            'Kiptoo','Mutua','Achieng','Kariuki','Waweru','Ouma',
            'Chebet','Mugo','Akinyi','Githinji','Koech','Nyambura',
            'Ondiek','Wangari'
        ]

        students = []
        for i in range(50):
            first = kenyan_first_names[i]
            last = random.choice(kenyan_last_names)
            email = f'student{i+1:02d}@strathmoreprimary.ac.ke'
            student, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    'school': school, 'role': 'student',
                    'full_name': f'{first} {last}',
                    'hashed_password': make_hashed('Student123!')
                }
            )
            meal_account, _ = MealAccount.objects.get_or_create(
                student=student,
                defaults={'balance_cents': random.randint(5000, 200000)}
            )
            students.append((student, meal_account))

        self.stdout.write(f'Students ready: {len(students)}')

        # Parents
        for i, (student, _) in enumerate(students[:20]):
            email = f'parent{i+1:02d}@gmail.com'
            User.objects.get_or_create(
                email=email,
                defaults={
                    'school': school, 'role': 'parent',
                    'full_name': f'Parent of {student.full_name}',
                    'hashed_password': make_hashed('Parent123!')
                }
            )

        # Terms
        terms = [
            {'name': 'Term 1 2026', 'start': date(2026, 1, 5),  'end': date(2026, 4, 3)},
            {'name': 'Term 2 2026', 'start': date(2026, 5, 4),  'end': date(2026, 8, 7)},
        ]

        all_school_days = []
        for term in terms:
            current = term['start']
            while current <= term['end']:
                if is_school_day(current):
                    week_num = get_term_week(current, term['start'])
                    all_school_days.append({
                        'date': current,
                        'term': term['name'],
                        'term_start': term['start'],
                        'week': week_num,
                        'is_exam': is_exam_week(week_num)
                    })
                current += timedelta(days=1)

        self.stdout.write(f'School days: {len(all_school_days)}')

        # Payment transactions
        tx_count = 0
        for student, meal_account in students:
            for _ in range(random.randint(8, 15)):
                day_info = random.choice(all_school_days)
                amount_cents = random.choice([10000, 20000, 30000, 50000])
                tx_dt = timezone.make_aware(
                    datetime.combine(day_info['date'],
                        datetime.min.time().replace(
                            hour=random.randint(6, 17),
                            minute=random.randint(0, 59)
                        ))
                )
                tx = PaymentTransaction.objects.create(
                    meal_account=meal_account,
                    amount_cents=amount_cents,
                    mpesa_reference=f'QK{random.randint(1000000,9999999)}',
                    status='confirmed',
                    callback_payload={'synthetic': True},
                )
                backdate(PaymentTransaction, tx.pk, tx_dt)
                meal_account.balance_cents += amount_cents
                meal_account.save()
                tx_count += 1

        self.stdout.write(f'Transactions: {tx_count}')

        # Meal distribution events
        dist_count = 0
        enrolment = len(students)
        for day_info in all_school_days:
            school_date = day_info['date']
            rate = get_attendance_rate(school_date, day_info['week'])
            num_eating = int(enrolment * rate)
            eating = random.sample(students, num_eating)
            for student, meal_account in eating:
                if meal_account.balance_cents < 5000:
                    continue
                event, created = MealDistributionEvent.objects.get_or_create(
                    meal_account=meal_account,
                    meal_date=school_date,
                    defaults={
                        'recorded_by': kitchen,
                        'meals_served': 1,
                    }
                )
                if created:
                    event_dt = timezone.make_aware(
                        datetime.combine(school_date,
                            datetime.min.time().replace(
                                hour=12,
                                minute=random.randint(0, 59)
                            ))
                    )
                    backdate(MealDistributionEvent, event.pk, event_dt)
                dist_count += 1

        self.stdout.write(f'Distribution events: {dist_count}')

        # Anomaly transactions
        for i in range(15):
            student, meal_account = random.choice(students)
            day_info = random.choice(all_school_days)
            amount = random.choice([500000, 750000, 1000000])
            tx_dt = timezone.make_aware(
                datetime.combine(day_info['date'],
                    datetime.min.time().replace(
                        hour=random.randint(0, 4),
                        minute=random.randint(0, 59)
                    ))
            )
            tx = PaymentTransaction.objects.create(
                meal_account=meal_account,
                amount_cents=amount,
                mpesa_reference=f'ANOM{random.randint(100000,999999)}',
                status='confirmed',
                callback_payload={'synthetic': True, 'anomalous': True},
            )
            backdate(PaymentTransaction, tx.pk, tx_dt)
            AnomalyFlag.objects.create(
                transaction=tx,
                anomaly_score=round(random.uniform(0.65, 0.95), 3),
                reviewed=random.choice([True, False]),
                review_notes='Synthetic anomaly for model training'
            )

        # Export CSV
        import csv, os
        csv_path = os.path.join('..', 'ml', 'data', 'meal_distribution.csv')
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        rows = []
        for term in terms:
            current = term['start']
            while current <= term['end']:
                if is_school_day(current):
                    week_num = get_term_week(current, term['start'])
                    meals = MealDistributionEvent.objects.filter(
                        meal_date=current,
                        meal_account__student__school=school
                    ).count()
                    if meals > 0:
                        rows.append({
                            'meal_date': current.isoformat(),
                            'term': term['name'],
                            'term_week': week_num,
                            'day_of_week': current.weekday(),
                            'is_exam_week': 1 if is_exam_week(week_num) else 0,
                            'student_enrolment': enrolment,
                            # Same-day ground truth — used only to derive the
                            # lagged attendance_rate feature below, never
                            # written to the CSV. Kept as-is it would let a
                            # model trivially back out meals_served from its
                            # own input (meals_served == attendance_rate *
                            # enrolment), and it isn't something a real
                            # forecast can know in advance anyway.
                            '_true_attendance_rate': round(meals / enrolment, 4),
                            'attendance_rate': 0,
                            'rolling_7day_avg': 0,
                            'meals_served': meals,
                        })
                current += timedelta(days=1)

        # Calculate rolling 7 day average of meals served (lagged — only
        # uses days strictly before the current one)
        for i, row in enumerate(rows):
            past = rows[max(0, i-7):i]
            if past:
                row['rolling_7day_avg'] = round(
                    sum(r['meals_served'] for r in past) / len(past), 2)
            else:
                row['rolling_7day_avg'] = row['meals_served']

        # attendance_rate feature: a lagged rolling average of attendance
        # over the past 7 school days, NOT the same-day value — this is
        # what's actually knowable at forecast time (GenerateForecastView
        # has to estimate it with a day-of-week heuristic for the same
        # reason). The first row in the dataset has no prior history, so
        # it falls back to a neutral default instead of leaking its own
        # same-day value.
        DEFAULT_ATTENDANCE_RATE = 0.85
        for i, row in enumerate(rows):
            past = rows[max(0, i-7):i]
            if past:
                row['attendance_rate'] = round(
                    sum(r['_true_attendance_rate'] for r in past) / len(past), 4)
            else:
                row['attendance_rate'] = DEFAULT_ATTENDANCE_RATE
        # Drop the temporary ground-truth field only after every row's
        # lagged average has been computed — earlier rows are still read
        # from `past` while later rows are being processed above.
        for row in rows:
            del row['_true_attendance_rate']

        fieldnames = ['meal_date', 'term', 'term_week', 'day_of_week',
                      'is_exam_week', 'student_enrolment', 'attendance_rate',
                      'rolling_7day_avg', 'meals_served']
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        self.stdout.write(f'CSV exported: {len(rows)} rows -> ml/data/meal_distribution.csv')
        self.stdout.write('='*50)
        self.stdout.write('DATA GENERATION COMPLETE — Ready for Sprint 4')
        self.stdout.write('='*50)
