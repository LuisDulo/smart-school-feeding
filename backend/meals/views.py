from datetime import date, datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db import transaction as db_transaction
from .models import (MealDistributionEvent, MealAccount,
                      User, PaymentTransaction, MenuItem, MealCombo)
from rest_framework import serializers
from core.permissions import IsKitchenStaff, IsAdminOrBursar, IsSchoolAdmin


class MenuItemSerializer(serializers.ModelSerializer):
    price_ksh = serializers.SerializerMethodField()

    class Meta:
        model = MenuItem
        fields = ['id', 'name', 'price_cents', 'price_ksh', 'is_active']

    def get_price_ksh(self, obj):
        return obj.price_cents / 100


class MealComboSerializer(serializers.ModelSerializer):
    items = MenuItemSerializer(many=True, read_only=True)
    total_price_cents = serializers.SerializerMethodField()
    total_price_ksh = serializers.SerializerMethodField()

    class Meta:
        model = MealCombo
        fields = ['id', 'name', 'items', 'total_price_cents',
                  'total_price_ksh', 'is_active']

    def get_total_price_cents(self, obj):
        return obj.total_price_cents()

    def get_total_price_ksh(self, obj):
        return obj.total_price_cents() / 100


class MealDistributionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(
        source='meal_account.student.full_name', read_only=True)
    student_id = serializers.IntegerField(
        source='meal_account.student.id', read_only=True)
    balance_after_ksh = serializers.SerializerMethodField()
    amount_ksh = serializers.SerializerMethodField()
    items = MenuItemSerializer(many=True, read_only=True)
    served_by_name = serializers.CharField(
        source='recorded_by.full_name', read_only=True, default=None)
    served_by_email = serializers.CharField(
        source='recorded_by.email', read_only=True, default=None)

    class Meta:
        model = MealDistributionEvent
        fields = ['id', 'student_name', 'student_id',
                  'meal_date', 'meals_served', 'items',
                  'amount_cents', 'amount_ksh',
                  'served_by_name', 'served_by_email',
                  'balance_after_ksh', 'created_at']

    def get_balance_after_ksh(self, obj):
        return obj.meal_account.balance_cents / 100

    def get_amount_ksh(self, obj):
        return obj.amount_cents / 100


class MenuItemListCreateView(APIView):
    """
    GET  /api/meals/menu/            — active menu items for the school
                                        (any authenticated staff)
    POST /api/meals/menu/            — add a menu item (admin only)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = MenuItem.objects.filter(
            school=request.user.school, is_active=True)
        return Response(MenuItemSerializer(items, many=True).data)

    def post(self, request):
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only school admins can manage the menu.'},
                status=status.HTTP_403_FORBIDDEN)

        name = request.data.get('name', '').strip()
        price_cents = request.data.get('price_cents')
        if not name or price_cents is None:
            return Response(
                {'error': 'name and price_cents are required.'},
                status=status.HTTP_400_BAD_REQUEST)
        try:
            price_cents = int(price_cents)
            if price_cents <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return Response({'error': 'price_cents must be a positive integer.'},
                            status=status.HTTP_400_BAD_REQUEST)

        item = MenuItem.objects.create(
            school=request.user.school, name=name, price_cents=price_cents)
        return Response(MenuItemSerializer(item).data,
                        status=status.HTTP_201_CREATED)


class MenuItemDetailView(APIView):
    """
    PATCH  /api/meals/menu/{id}/ — edit name/price/active (admin only)
    DELETE /api/meals/menu/{id}/ — deactivate (soft-delete, admin only)
    """
    permission_classes = [IsAuthenticated, IsSchoolAdmin]

    def _get_item(self, request, item_id):
        return MenuItem.objects.get(id=item_id, school=request.user.school)

    def patch(self, request, item_id):
        try:
            item = self._get_item(request, item_id)
        except MenuItem.DoesNotExist:
            return Response({'error': 'Menu item not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        if 'name' in request.data:
            item.name = request.data['name'].strip()
        if 'price_cents' in request.data:
            try:
                price_cents = int(request.data['price_cents'])
                if price_cents <= 0:
                    raise ValueError
                item.price_cents = price_cents
            except (TypeError, ValueError):
                return Response({'error': 'price_cents must be a positive integer.'},
                                status=status.HTTP_400_BAD_REQUEST)
        if 'is_active' in request.data:
            item.is_active = bool(request.data['is_active'])
        item.save()
        return Response(MenuItemSerializer(item).data)

    def delete(self, request, item_id):
        try:
            item = self._get_item(request, item_id)
        except MenuItem.DoesNotExist:
            return Response({'error': 'Menu item not found.'},
                            status=status.HTTP_404_NOT_FOUND)
        item.is_active = False
        item.save()
        return Response({'message': f'{item.name} removed from the menu.'})


class MealComboListCreateView(APIView):
    """
    A named shortcut for a common combination of menu items (e.g.
    "Lunch Special" = Rice + Beans + Sukuma), so kitchen staff can search
    for one name instead of picking every item each time. Price is always
    the live sum of its items — never stored separately.
    GET  /api/meals/combos/  — active combos for the school (any staff)
    POST /api/meals/combos/  — create a combo (admin only)
    Body: { name, item_ids: [1, 2, 3] }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        combos = MealCombo.objects.filter(
            school=request.user.school, is_active=True
        ).prefetch_related('items')
        return Response(MealComboSerializer(combos, many=True).data)

    def post(self, request):
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only school admins can manage meal combos.'},
                status=status.HTTP_403_FORBIDDEN)

        name = request.data.get('name', '').strip()
        item_ids = request.data.get('item_ids') or []
        if not name:
            return Response({'error': 'name is required.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not item_ids:
            return Response({'error': 'Select at least one item for the combo.'},
                            status=status.HTTP_400_BAD_REQUEST)

        items = list(MenuItem.objects.filter(
            id__in=item_ids, school=request.user.school, is_active=True))
        if len(items) != len(set(item_ids)):
            return Response(
                {'error': 'One or more selected items are unavailable.'},
                status=status.HTTP_400_BAD_REQUEST)

        combo = MealCombo.objects.create(school=request.user.school, name=name)
        combo.items.set(items)
        return Response(MealComboSerializer(combo).data,
                        status=status.HTTP_201_CREATED)


class MealComboDetailView(APIView):
    """
    PATCH  /api/meals/combos/{id}/ — edit name/items/active (admin only)
    DELETE /api/meals/combos/{id}/ — deactivate (soft-delete, admin only)
    """
    permission_classes = [IsAuthenticated, IsSchoolAdmin]

    def _get_combo(self, request, combo_id):
        return MealCombo.objects.get(id=combo_id, school=request.user.school)

    def patch(self, request, combo_id):
        try:
            combo = self._get_combo(request, combo_id)
        except MealCombo.DoesNotExist:
            return Response({'error': 'Meal combo not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        if 'name' in request.data:
            combo.name = request.data['name'].strip()
        if 'item_ids' in request.data:
            item_ids = request.data['item_ids'] or []
            if not item_ids:
                return Response(
                    {'error': 'Select at least one item for the combo.'},
                    status=status.HTTP_400_BAD_REQUEST)
            items = list(MenuItem.objects.filter(
                id__in=item_ids, school=request.user.school, is_active=True))
            if len(items) != len(set(item_ids)):
                return Response(
                    {'error': 'One or more selected items are unavailable.'},
                    status=status.HTTP_400_BAD_REQUEST)
            combo.items.set(items)
        if 'is_active' in request.data:
            combo.is_active = bool(request.data['is_active'])
        combo.save()
        return Response(MealComboSerializer(combo).data)

    def delete(self, request, combo_id):
        try:
            combo = self._get_combo(request, combo_id)
        except MealCombo.DoesNotExist:
            return Response({'error': 'Meal combo not found.'},
                            status=status.HTTP_404_NOT_FOUND)
        combo.is_active = False
        combo.save()
        return Response({'message': f'{combo.name} removed.'})


class RecordMealView(APIView):
    """
    Kitchen staff records a meal served to a student, picking which menu
    items they took. The total cost is the sum of the selected items'
    prices, deducted from the student's balance. If the balance would go
    negative, it's still allowed as long as it doesn't exceed the
    account's approved credit_limit_cents (see CreditRequest).
    POST /api/meals/serve/
    Body: { student_id: int, item_ids: [1, 2, 3] }
    """
    permission_classes = [IsAuthenticated, IsKitchenStaff]

    def post(self, request):
        student_id = request.data.get('student_id')
        item_ids = request.data.get('item_ids') or []
        if not student_id:
            return Response({'error': 'student_id is required.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not item_ids:
            return Response({'error': 'Select at least one food item.'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            student = User.objects.get(id=student_id, role='student')
            meal_account = student.meal_account
        except (User.DoesNotExist, MealAccount.DoesNotExist):
            return Response({'error': 'Student or meal account not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        items = list(MenuItem.objects.filter(
            id__in=item_ids, school=request.user.school, is_active=True))
        if len(items) != len(set(item_ids)):
            return Response(
                {'error': 'One or more selected items are unavailable.'},
                status=status.HTTP_400_BAD_REQUEST)

        total_cents = sum(item.price_cents for item in items)

        today = date.today()
        if MealDistributionEvent.objects.filter(
                meal_account=meal_account, meal_date=today).exists():
            return Response({
                'error': 'Meal already recorded for this student today.',
                'student': student.full_name,
                'date': str(today)
            }, status=status.HTTP_409_CONFLICT)

        if meal_account.balance_cents - total_cents < -meal_account.credit_limit_cents:
            return Response({
                'error': 'Insufficient balance (including approved credit).',
                'balance_ksh': meal_account.balance_cents / 100,
                'credit_limit_ksh': meal_account.credit_limit_cents / 100,
                'required_ksh': total_cents / 100
            }, status=status.HTTP_402_PAYMENT_REQUIRED)

        # request.user is already resolved to a meals.User instance by
        # MealsJWTAuthentication (see core/authentication.py). This is
        # who "served by" refers to — the authenticated kitchen account,
        # not a free-typed name/email that could be spoofed.
        recorded_by = request.user

        with db_transaction.atomic():
            event = MealDistributionEvent.objects.create(
                meal_account=meal_account,
                recorded_by=recorded_by,
                meal_date=today,
                meals_served=1,
                amount_cents=total_cents,
            )
            event.items.set(items)
            meal_account.balance_cents -= total_cents
            meal_account.save()

        return Response({
            'message': f'Meal recorded for {student.full_name}.',
            'student': student.full_name,
            'items': [i.name for i in items],
            'date': str(today),
            'deducted_ksh': total_cents / 100,
            'new_balance_ksh': meal_account.balance_cents / 100,
            'served_by': recorded_by.full_name,
            'served_by_email': recorded_by.email,
            'event_id': event.id
        }, status=status.HTTP_201_CREATED)


class DailyDistributionLogView(APIView):
    """
    Get today's meal distribution log for the school.
    GET /api/meals/log/
    GET /api/meals/log/?date=2026-06-15
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        log_date_str = request.query_params.get('date')

        if log_date_str:
            try:
                log_date = datetime.strptime(log_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            log_date = date.today()

        events = MealDistributionEvent.objects.filter(
            meal_account__student__school=user.school,
            meal_date=log_date
        ).select_related(
            'meal_account__student', 'recorded_by'
        ).prefetch_related('items').order_by('-created_at')

        total = events.count()
        enrolment = User.objects.filter(
            school=user.school, role='student').count()

        return Response({
            'date': str(log_date),
            'total_meals_served': total,
            'enrolment': enrolment,
            'attendance_rate': round(total / enrolment, 4) if enrolment else 0,
            'events': MealDistributionSerializer(events, many=True).data
        })


class ConsumptionHistoryView(APIView):
    """
    A parent's (or student's own) meal consumption history — what was
    served, what it cost, and when. Reuses MealDistributionEvent, scoped
    to the caller's own account (student) or a linked child's (parent).
    GET /api/meals/consumption/
    GET /api/meals/consumption/?meal_account_id=  — pick a child, if a
        parent has more than one linked
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from payments.views import resolve_meal_account
        meal_account_id = request.query_params.get('meal_account_id')
        try:
            meal_account = resolve_meal_account(request.user, meal_account_id)
        except MealAccount.DoesNotExist:
            return Response({'error': 'Meal account not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        events = MealDistributionEvent.objects.filter(
            meal_account=meal_account
        ).select_related('recorded_by').prefetch_related(
            'items').order_by('-meal_date', '-created_at')[:90]

        return Response({
            'student_name': meal_account.student.full_name,
            'events': MealDistributionSerializer(events, many=True).data
        })


class StudentLookupView(APIView):
    """
    Kitchen staff looks up a student by ID or name.
    GET /api/meals/lookup/?q=John
    GET /api/meals/lookup/?id=5
    """
    permission_classes = [IsAuthenticated, IsKitchenStaff]

    def get(self, request):
        user = request.user

        student_id = request.query_params.get('id')
        query = request.query_params.get('q')

        if student_id:
            try:
                student = User.objects.get(
                    id=student_id, role='student',
                    school=user.school)
            except User.DoesNotExist:
                return Response({'error': 'Student not found.'},
                                status=status.HTTP_404_NOT_FOUND)
            students = [student]
        elif query:
            students = User.objects.filter(
                school=user.school,
                role='student',
                full_name__icontains=query
            )[:10]
        else:
            return Response(
                {'error': 'Provide id or q parameter.'},
                status=status.HTTP_400_BAD_REQUEST)

        results = []
        today = date.today()
        for s in students:
            try:
                meal_account = s.meal_account
                already_served = MealDistributionEvent.objects.filter(
                    meal_account=meal_account,
                    meal_date=today
                ).exists()
                results.append({
                    'id': s.id,
                    'full_name': s.full_name,
                    'email': s.email,
                    'balance_ksh': meal_account.balance_cents / 100,
                    'balance_cents': meal_account.balance_cents,
                    'credit_limit_ksh': meal_account.credit_limit_cents / 100,
                    'available_to_spend_ksh':
                        meal_account.available_to_spend_cents() / 100,
                    'is_low_balance': meal_account.balance_cents < 10000,
                    'already_served_today': already_served,
                    # Affordability now depends on which items get picked
                    # at serve time (variable-price menu), so eligibility
                    # here is just "hasn't already eaten today" — the
                    # actual balance/credit check happens in
                    # RecordMealView against the real selected total.
                    'eligible': not already_served
                })
            except MealAccount.DoesNotExist:
                continue

        return Response({'students': results, 'count': len(results)})
