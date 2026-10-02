import logging
from datetime import date, timedelta
from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from meals.models import (
    School, User, MealAccount, PaymentTransaction,
    MealDistributionEvent, AnomalyFlag, DemandForecast
)
from core.permissions import IsSuperAdmin
from .password_rules import password_problems
from core.pagination import paginate_queryset

logger = logging.getLogger(__name__)

# Webmasters Kenya's own School row is an internal organisation record
# (it has a superadmin user, not a school admin), not a real school with
# students/meals — every superadmin query excludes it by name so network
# stats and school lists never include Webmasters Kenya itself.
WEBMASTERS_KENYA = 'Webmasters Kenya'


def school_metrics(school, today=None):
    """Return a metrics dict for a single school."""
    if today is None:
        today = date.today()

    students = User.objects.filter(school=school, role='student')
    student_count = students.count()
    staff_count = User.objects.filter(
        school=school,
        role__in=['admin', 'bursar', 'kitchen']
    ).count()

    meals_today = MealDistributionEvent.objects.filter(
        meal_account__student__school=school,
        meal_date=today
    ).count()

    collected_today = PaymentTransaction.objects.filter(
        meal_account__student__school=school,
        status='confirmed',
        created_at__date=today
    ).aggregate(total=Sum('amount_cents'))['total'] or 0

    pending_flags = AnomalyFlag.objects.filter(
        transaction__meal_account__student__school=school,
        reviewed=False
    ).count()

    low_balance = MealAccount.objects.filter(
        student__school=school,
        balance_cents__lt=10000
    ).count()

    total_balance = MealAccount.objects.filter(
        student__school=school
    ).aggregate(total=Sum('balance_cents'))['total'] or 0

    attendance_rate = round(
        meals_today / student_count, 4
    ) if student_count else 0

    last_event = MealDistributionEvent.objects.filter(
        meal_account__student__school=school
    ).order_by('-created_at').first()

    return {
        'id': school.id,
        'name': school.name,
        'county': school.county,
        'contact_email': school.contact_email,
        'student_count': student_count,
        'staff_count': staff_count,
        'meals_today': meals_today,
        'attendance_rate_today': attendance_rate,
        'collected_today_ksh': collected_today / 100,
        'pending_flags': pending_flags,
        'low_balance_count': low_balance,
        'total_balance_pool_ksh': total_balance / 100,
        'avg_balance_ksh': round(
            total_balance / student_count / 100, 2
        ) if student_count else 0,
        'last_activity': str(last_event.created_at)
            if last_event else None,
    }


class SuperAdminOverviewView(APIView):
    """
    Aggregated stats across ALL schools.
    GET /api/superadmin/overview/
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        today = date.today()

        schools = School.objects.exclude(name=WEBMASTERS_KENYA)

        total_schools = schools.count()
        total_students = User.objects.filter(
            school__in=schools, role='student').count()
        total_staff = User.objects.filter(
            school__in=schools,
            role__in=['admin', 'bursar', 'kitchen']
        ).count()

        meals_today = MealDistributionEvent.objects.filter(
            meal_account__student__school__in=schools,
            meal_date=today
        ).count()

        collected_today = PaymentTransaction.objects.filter(
            meal_account__student__school__in=schools,
            status='confirmed',
            created_at__date=today
        ).aggregate(total=Sum('amount_cents'))['total'] or 0

        active_flags = AnomalyFlag.objects.filter(
            transaction__meal_account__student__school__in=schools,
            reviewed=False
        ).count()

        low_balance_total = MealAccount.objects.filter(
            student__school__in=schools,
            balance_cents__lt=10000
        ).count()

        # 14-day meal trend per school
        trend_data = []
        for i in range(13, -1, -1):
            d = today - timedelta(days=i)
            if d.weekday() >= 5:
                continue
            day_entry = {
                'date': str(d),
                'day': d.strftime('%a %d %b'),
                'total': 0,
                'schools': {}
            }
            for school in schools:
                count = MealDistributionEvent.objects.filter(
                    meal_account__student__school=school,
                    meal_date=d
                ).count()
                day_entry['schools'][school.name] = count
                day_entry['total'] += count
            trend_data.append(day_entry)

        # Recent activity feed (last 15 events across all schools)
        recent_events = MealDistributionEvent.objects.filter(
            meal_account__student__school__in=schools
        ).select_related(
            'meal_account__student__school',
            'recorded_by'
        ).order_by('-created_at')[:15]

        recent_payments = PaymentTransaction.objects.filter(
            meal_account__student__school__in=schools,
            status='confirmed'
        ).select_related(
            'meal_account__student__school'
        ).order_by('-created_at')[:5]

        activity_feed = []
        for e in recent_events:
            activity_feed.append({
                'type': 'meal',
                'school': e.meal_account.student.school.name,
                'description': f'{e.meal_account.student.full_name} collected meal',
                'timestamp': str(e.created_at),
            })
        for p in recent_payments:
            activity_feed.append({
                'type': 'payment',
                'school': p.meal_account.student.school.name,
                'description': f'KES {p.amount_cents/100:.0f} top-up received',
                'timestamp': str(p.created_at),
            })
        activity_feed.sort(
            key=lambda x: x['timestamp'], reverse=True)

        # Per-school performance table
        school_performance = []
        for school in schools:
            sc = User.objects.filter(
                school=school, role='student').count()
            mt = MealDistributionEvent.objects.filter(
                meal_account__student__school=school,
                meal_date=today
            ).count()
            ct = PaymentTransaction.objects.filter(
                meal_account__student__school=school,
                status='confirmed',
                created_at__date=today
            ).aggregate(t=Sum('amount_cents'))['t'] or 0
            pf = AnomalyFlag.objects.filter(
                transaction__meal_account__student__school=school,
                reviewed=False
            ).count()
            school_performance.append({
                'id': school.id,
                'name': school.name,
                'students': sc,
                'meals_today': mt,
                'target': sc,
                'attendance_pct': round(mt/sc*100, 1) if sc else 0,
                'collected_ksh': ct / 100,
                'pending_flags': pf,
                'below_target': (mt / sc < 0.80) if sc else False,
            })

        return Response({
            'summary': {
                'total_schools': total_schools,
                'total_students': total_students,
                'total_staff': total_staff,
                'meals_today': meals_today,
                'collected_today_ksh': collected_today / 100,
                'active_flags': active_flags,
                'low_balance_total': low_balance_total,
            },
            'school_performance': school_performance,
            'meal_trend_14days': trend_data,
            'activity_feed': activity_feed[:15],
            'school_names': [s.name for s in schools],
        })


class SuperAdminSchoolListView(APIView):
    """
    Full metrics for every school.
    GET /api/superadmin/schools/
    POST /api/superadmin/schools/  <- create new school
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        schools = School.objects.exclude(name=WEBMASTERS_KENYA)
        return Response({
            'schools': [school_metrics(s) for s in schools],
            'total': schools.count(),
        })

    def post(self, request):
        name = request.data.get('name', '').strip()
        county = request.data.get('county', '').strip()
        contact_email = request.data.get('contact_email', '').strip()
        admin_name = request.data.get('admin_name', '').strip()
        admin_email = request.data.get('admin_email', '').strip()
        admin_password = request.data.get('admin_password', '').strip()

        if not all([name, county, contact_email]):
            return Response(
                {'error': 'name, county and contact_email are required.'},
                status=status.HTTP_400_BAD_REQUEST)

        if School.objects.filter(name=name).exists():
            return Response(
                {'error': f'A school named "{name}" already exists.'},
                status=status.HTTP_400_BAD_REQUEST)

        if admin_email and admin_password:
            problems = password_problems(
                admin_password, admin_name or f'{name} Admin', admin_email)
            if problems:
                return Response({'error': ' '.join(problems)},
                                status=status.HTTP_400_BAD_REQUEST)

        school = School.objects.create(
            name=name,
            county=county,
            contact_email=contact_email,
        )

        # Create admin account if provided
        admin_user = None
        if admin_email and admin_password:
            import bcrypt
            if User.objects.filter(email=admin_email).exists():
                return Response({
                    'message': f'School "{name}" created, but the admin '
                               f'account was not: a user with email '
                               f'"{admin_email}" already exists.',
                    'school_id': school.id,
                    'admin_email': None,
                }, status=status.HTTP_201_CREATED)
            hashed = bcrypt.hashpw(
                admin_password.encode(), bcrypt.gensalt()
            ).decode()
            admin_user = User.objects.create(
                school=school,
                role='admin',
                full_name=admin_name or f'{name} Admin',
                email=admin_email,
                hashed_password=hashed
            )

        return Response({
            'message': f'School "{name}" created successfully.',
            'school_id': school.id,
            'admin_email': admin_user.email if admin_user else None,
        }, status=status.HTTP_201_CREATED)


class SuperAdminSchoolDetailView(APIView):
    """
    Detailed view of one school -- same data as school admin sees.
    GET /api/superadmin/schools/{school_id}/
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request, school_id):
        try:
            school = School.objects.get(id=school_id)
        except School.DoesNotExist:
            return Response({'error': 'School not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        today = date.today()
        metrics = school_metrics(school)

        # 7-day trend for this school
        trend = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            count = MealDistributionEvent.objects.filter(
                meal_account__student__school=school,
                meal_date=d
            ).count()
            collected = PaymentTransaction.objects.filter(
                meal_account__student__school=school,
                status='confirmed',
                created_at__date=d
            ).aggregate(t=Sum('amount_cents'))['t'] or 0
            trend.append({
                'date': str(d),
                'day': d.strftime('%a'),
                'meals': count,
                'collected_ksh': collected / 100,
            })

        # Student balances
        accounts = MealAccount.objects.filter(
            student__school=school
        ).select_related('student').order_by('balance_cents')[:20]

        balances = [{
            'student_name': a.student.full_name,
            'balance_ksh': a.balance_cents / 100,
            'is_low': a.balance_cents < 10000,
        } for a in accounts]

        # Recent flags
        flags = AnomalyFlag.objects.filter(
            transaction__meal_account__student__school=school,
            reviewed=False
        ).select_related(
            'transaction__meal_account__student'
        ).order_by('-flagged_at')[:5]

        flag_list = [{
            'id': f.id,
            'student': f.transaction.meal_account.student.full_name,
            'amount_ksh': f.transaction.amount_cents / 100,
            'score': f.anomaly_score,
            'flagged_at': str(f.flagged_at),
        } for f in flags]

        return Response({
            'school': metrics,
            'trend_7days': trend,
            'low_balance_students': balances,
            'pending_flags': flag_list,
        })


class SuperAdminStudentListView(APIView):
    """
    All students across all schools with search and filter.
    GET /api/superadmin/students/
    GET /api/superadmin/students/?school_id=1
    GET /api/superadmin/students/?status=low
    GET /api/superadmin/students/?q=John
    GET /api/superadmin/students/?limit=50&offset=50
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        schools = School.objects.exclude(name=WEBMASTERS_KENYA)
        students = User.objects.filter(
            school__in=schools, role='student'
        ).select_related('school', 'meal_account')

        school_id = request.query_params.get('school_id')
        if school_id:
            students = students.filter(school_id=school_id)

        q = request.query_params.get('q')
        if q:
            students = students.filter(full_name__icontains=q)

        # Filtered at the ORM level, before pagination, so matches
        # aren't silently lost past the page slice.
        bal_status = request.query_params.get('status')
        if bal_status == 'low':
            students = students.filter(
                meal_account__balance_cents__lt=10000)
        elif bal_status == 'zero':
            students = students.filter(meal_account__balance_cents=0)

        page, meta = paginate_queryset(request, students, default_limit=200)

        results = []
        for s in page:
            try:
                ma = s.meal_account
                bal = ma.balance_cents
                last_meal = MealDistributionEvent.objects.filter(
                    meal_account=ma
                ).order_by('-meal_date').first()

                results.append({
                    'id': s.id,
                    'full_name': s.full_name,
                    'email': s.email,
                    'school': s.school.name,
                    'school_id': s.school_id,
                    'balance_ksh': bal / 100,
                    'is_low': bal < 10000,
                    'is_zero': bal == 0,
                    'last_meal': str(last_meal.meal_date)
                        if last_meal else None,
                })
            except MealAccount.DoesNotExist:
                continue

        return Response({
            'students': results,
            'count': len(results),
            **meta,
        })


class SuperAdminStaffListView(APIView):
    """
    All staff across all schools.
    GET /api/superadmin/staff/
    GET /api/superadmin/staff/?school_id=1
    POST /api/superadmin/staff/  <- create staff account
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        schools = School.objects.exclude(name=WEBMASTERS_KENYA)
        staff = User.objects.filter(
            school__in=schools,
            role__in=['admin', 'bursar', 'kitchen']
        ).select_related('school').order_by('school__name', 'role')

        school_id = request.query_params.get('school_id')
        if school_id:
            staff = staff.filter(school_id=school_id)

        return Response({
            'staff': [{
                'id': u.id,
                'full_name': u.full_name,
                'email': u.email,
                'role': u.role,
                'school': u.school.name,
                'school_id': u.school_id,
                'created_at': str(u.created_at),
            } for u in staff],
            'count': staff.count(),
        })

    def post(self, request):
        import bcrypt
        school_id = request.data.get('school_id')
        role = request.data.get('role')
        full_name = request.data.get('full_name', '').strip()
        email = request.data.get('email', '').strip()
        password = request.data.get('password', '').strip()

        if not all([school_id, role, full_name, email, password]):
            return Response(
                {'error': 'school_id, role, full_name, email and password are all required.'},
                status=status.HTTP_400_BAD_REQUEST)

        if role not in ['admin', 'bursar', 'kitchen']:
            return Response(
                {'error': 'Role must be admin, bursar, or kitchen.'},
                status=status.HTTP_400_BAD_REQUEST)

        try:
            school = School.objects.get(id=school_id)
        except School.DoesNotExist:
            return Response({'error': 'School not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        if User.objects.filter(email=email).exists():
            return Response(
                {'error': 'A user with this email already exists.'},
                status=status.HTTP_400_BAD_REQUEST)

        problems = password_problems(password, full_name, email)
        if problems:
            return Response({'error': ' '.join(problems)},
                            status=status.HTTP_400_BAD_REQUEST)

        hashed = bcrypt.hashpw(
            password.encode(), bcrypt.gensalt()).decode()
        user = User.objects.create(
            school=school, role=role,
            full_name=full_name, email=email,
            hashed_password=hashed
        )
        return Response({
            'message': f'{role.capitalize()} account created for {school.name}.',
            'user_id': user.id,
            'email': user.email,
        }, status=status.HTTP_201_CREATED)


class SuperAdminAnomalyView(APIView):
    """
    All anomaly flags across all schools.
    GET /api/superadmin/anomalies/
    GET /api/superadmin/anomalies/?school_id=1
    GET /api/superadmin/anomalies/?severity=HIGH
    GET /api/superadmin/anomalies/?reviewed=false
    GET /api/superadmin/anomalies/?limit=50&offset=50
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        schools = School.objects.exclude(name=WEBMASTERS_KENYA)
        flags = AnomalyFlag.objects.filter(
            transaction__meal_account__student__school__in=schools
        ).select_related(
            'transaction__meal_account__student__school',
            'reviewed_by'
        ).order_by('-flagged_at')

        school_id = request.query_params.get('school_id')
        if school_id:
            flags = flags.filter(
                transaction__meal_account__student__school_id=school_id)

        reviewed = request.query_params.get('reviewed')
        if reviewed == 'false':
            flags = flags.filter(reviewed=False)
        elif reviewed == 'true':
            flags = flags.filter(reviewed=True)

        # Filtered at the ORM level, before pagination, so matches
        # aren't silently lost past the page slice.
        sev_filter = request.query_params.get('severity')
        if sev_filter == 'HIGH':
            flags = flags.filter(anomaly_score__gte=0.80)
        elif sev_filter == 'MEDIUM':
            flags = flags.filter(anomaly_score__gte=0.65,
                                  anomaly_score__lt=0.80)
        elif sev_filter == 'LOW':
            flags = flags.filter(anomaly_score__lt=0.65)

        pending = flags.filter(reviewed=False).count()
        high = flags.filter(anomaly_score__gte=0.80).count()

        page, meta = paginate_queryset(request, flags, default_limit=200)

        result = []
        for f in page:
            score = f.anomaly_score
            severity = 'HIGH' if score >= 0.80 else \
                       'MEDIUM' if score >= 0.65 else 'LOW'
            result.append({
                'id': f.id,
                'school': f.transaction.meal_account
                           .student.school.name,
                'school_id': f.transaction.meal_account
                              .student.school_id,
                'student': f.transaction.meal_account
                            .student.full_name,
                'amount_ksh': f.transaction.amount_cents / 100,
                'mpesa_ref': f.transaction.mpesa_reference,
                'anomaly_score': score,
                'severity': severity,
                'flagged_at': str(f.flagged_at),
                'reviewed': f.reviewed,
                'reviewed_by': f.reviewed_by.full_name
                    if f.reviewed_by else None,
            })

        return Response({
            'total': meta['count'],
            'pending': pending,
            'high_severity': high,
            'flags': result,
            **meta,
        })


class SuperAdminAnalyticsView(APIView):
    """
    Cross-school analytics for charts.
    GET /api/superadmin/analytics/
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        schools = School.objects.exclude(name=WEBMASTERS_KENYA)
        today = date.today()
        days = int(request.query_params.get('days', 30))
        since = today - timedelta(days=days)

        # Weekly collections per school
        weekly_collections = []
        for school in schools:
            weekly = []
            for i in range(3, -1, -1):
                week_start = today - timedelta(weeks=i+1)
                week_end = today - timedelta(weeks=i)
                total = PaymentTransaction.objects.filter(
                    meal_account__student__school=school,
                    status='confirmed',
                    created_at__date__gte=week_start,
                    created_at__date__lt=week_end,
                ).aggregate(t=Sum('amount_cents'))['t'] or 0
                weekly.append({
                    'week': f'W-{i+1}',
                    'collected_ksh': total / 100
                })
            weekly_collections.append({
                'school': school.name,
                'weekly': weekly,
            })

        # Balance distribution all schools
        all_balances = MealAccount.objects.filter(
            student__school__in=schools
        ).values_list('balance_cents', flat=True)

        brackets = {
            'KES 0': 0,
            'KES 1-100': 0,
            'KES 100-500': 0,
            'KES 500-1000': 0,
            'KES 1000+': 0,
        }
        for b in all_balances:
            ksh = b / 100
            if ksh == 0:
                brackets['KES 0'] += 1
            elif ksh < 100:
                brackets['KES 1-100'] += 1
            elif ksh < 500:
                brackets['KES 100-500'] += 1
            elif ksh < 1000:
                brackets['KES 500-1000'] += 1
            else:
                brackets['KES 1000+'] += 1

        # Forecast accuracy per school
        forecast_accuracy = []
        for school in schools:
            forecasts = DemandForecast.objects.filter(
                school=school,
                forecast_date__gte=since,
                forecast_date__lte=today
            )
            accuracy_rows = []
            for f in forecasts:
                actual = MealDistributionEvent.objects.filter(
                    meal_account__student__school=school,
                    meal_date=f.forecast_date
                ).count()
                if actual > 0:
                    mae = abs(f.predicted_meals - actual)
                    accuracy_rows.append(mae)
            avg_mae = round(
                sum(accuracy_rows) / len(accuracy_rows), 1
            ) if accuracy_rows else None
            forecast_accuracy.append({
                'school': school.name,
                'avg_mae': avg_mae,
                'forecasts_evaluated': len(accuracy_rows),
            })

        return Response({
            'weekly_collections_per_school': weekly_collections,
            'balance_distribution': [
                {'bracket': k, 'count': v}
                for k, v in brackets.items()
            ],
            'forecast_accuracy': forecast_accuracy,
            'period_days': days,
        })


class SuperAdminReportView(APIView):
    """
    Network-wide CSV reports.
    GET /api/superadmin/reports/payments/
    GET /api/superadmin/reports/meals/
    GET /api/superadmin/reports/summary/
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request, report_type):
        import csv
        import io
        from django.http import HttpResponse

        schools = School.objects.exclude(name=WEBMASTERS_KENYA)
        days = int(request.query_params.get('days', 90))
        since = date.today() - timedelta(days=days)

        if report_type == 'payments':
            txns = PaymentTransaction.objects.filter(
                meal_account__student__school__in=schools,
                status='confirmed',
                created_at__date__gte=since
            ).select_related(
                'meal_account__student__school'
            ).order_by('-created_at')

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                'School', 'Date', 'Student Name',
                'Amount (KES)', 'M-Pesa Reference', 'Flagged'
            ])
            flagged_tx_ids = set(
                AnomalyFlag.objects.filter(
                    transaction__in=txns
                ).values_list('transaction_id', flat=True)
            )
            for tx in txns:
                writer.writerow([
                    tx.meal_account.student.school.name,
                    tx.created_at.date(),
                    tx.meal_account.student.full_name,
                    tx.amount_cents / 100,
                    tx.mpesa_reference or '-',
                    'YES' if tx.id in flagged_tx_ids else 'NO',
                ])
            output.seek(0)
            response = HttpResponse(output, content_type='text/csv')
            response['Content-Disposition'] = (
                f'attachment; filename="network_payments_{date.today()}.csv"')
            return response

        elif report_type == 'meals':
            events = MealDistributionEvent.objects.filter(
                meal_account__student__school__in=schools,
                meal_date__gte=since
            ).select_related(
                'meal_account__student__school',
                'recorded_by'
            ).order_by('-meal_date')

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                'School', 'Date', 'Student Name',
                'Meals Served', 'Recorded By'
            ])
            for e in events:
                writer.writerow([
                    e.meal_account.student.school.name,
                    e.meal_date,
                    e.meal_account.student.full_name,
                    e.meals_served,
                    e.recorded_by.full_name if e.recorded_by else '-',
                ])
            output.seek(0)
            response = HttpResponse(output, content_type='text/csv')
            response['Content-Disposition'] = (
                f'attachment; filename="network_meals_{date.today()}.csv"')
            return response

        elif report_type == 'summary':
            summary = []
            for school in schools:
                sc = User.objects.filter(
                    school=school, role='student').count()
                total_collected = PaymentTransaction.objects.filter(
                    meal_account__student__school=school,
                    status='confirmed',
                    created_at__date__gte=since
                ).aggregate(t=Sum('amount_cents'))['t'] or 0
                meals = MealDistributionEvent.objects.filter(
                    meal_account__student__school=school,
                    meal_date__gte=since
                ).count()
                flags = AnomalyFlag.objects.filter(
                    transaction__meal_account__student__school=school
                ).count()
                summary.append({
                    'school': school.name,
                    'county': school.county,
                    'students': sc,
                    'total_collected_ksh': total_collected / 100,
                    'total_meals_served': meals,
                    'anomaly_flags': flags,
                    'period_days': days,
                })
            return Response({
                'network_summary': summary,
                'generated_at': str(date.today()),
                'period_days': days,
            })

        return Response({'error': 'Invalid report type.'},
                        status=status.HTTP_400_BAD_REQUEST)
