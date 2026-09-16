from django.db import models


class School(models.Model):
    name = models.CharField(max_length=255)
    county = models.CharField(max_length=100)
    contact_email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'schools'


class User(models.Model):
    ROLE_CHOICES = [
        ('parent', 'Parent'),
        ('student', 'Student'),
        ('kitchen', 'Kitchen Staff'),
        ('bursar', 'Bursar'),
        ('admin', 'School Admin'),
        ('superadmin', 'Super Admin'),
    ]
    school = models.ForeignKey(School, on_delete=models.CASCADE,
                               related_name='users')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    hashed_password = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.role})"

    # meals.User is a plain business-logic model, not Django's
    # AUTH_USER_MODEL — but DRF's IsAuthenticated permission (and our own
    # role-based permission classes in core/permissions.py) expect
    # request.user to expose is_authenticated/is_anonymous. Any instance
    # resolved by MealsJWTAuthentication came from a validated token, so it
    # is by definition authenticated.
    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    class Meta:
        db_table = 'users'


class MealAccount(models.Model):
    student = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name='meal_account',
        limit_choices_to={'role': 'student'}
    )
    # Parents/guardians linked to this account. Many-to-many because a
    # parent can have several children and (occasionally) a student has
    # more than one registered guardian. Replaces the old "first student
    # in the same school" placeholder that payments/views.py used to
    # stand in for a real parent-student relationship.
    guardians = models.ManyToManyField(
        User, related_name='linked_meal_accounts', blank=True,
        limit_choices_to={'role': 'parent'}
    )
    balance_cents = models.IntegerField(default=0)
    # Approved overdraft: how far below zero this account may go before
    # RecordMealView refuses to serve a meal. Raised by an admin approving
    # a CreditRequest; never touched by ordinary top-ups or meal serving.
    credit_limit_cents = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.full_name} — KES {self.balance_cents / 100:.2f}"

    def get_balance_ksh(self):
        return self.balance_cents / 100

    def is_low_balance(self):
        return self.balance_cents < 10000  # below KES 100

    def available_to_spend_cents(self):
        """Balance plus whatever overdraft has been approved."""
        return self.balance_cents + self.credit_limit_cents

    class Meta:
        db_table = 'meal_accounts'


class MenuItem(models.Model):
    """A priced food item a school offers, e.g. beans=KES 30, rice=KES 30,
    sukuma=KES 10. Kitchen staff pick items when serving a student; the
    meal's total cost is the sum of the selected items' prices."""
    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name='menu_items')
    name = models.CharField(max_length=100)
    price_cents = models.IntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} — KES {self.price_cents / 100:.2f}"

    class Meta:
        db_table = 'menu_items'
        ordering = ['name']


class MealCombo(models.Model):
    """A named shortcut for a common combination of menu items, e.g.
    "Lunch Special" = Rice + Beans + Sukuma. Kitchen staff can search for
    this by name instead of picking each item individually. Its price is
    always the live sum of its component items' prices (not stored), so
    it never drifts out of sync when an admin edits an item's price."""
    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name='meal_combos')
    name = models.CharField(max_length=100)
    items = models.ManyToManyField(MenuItem, related_name='combos')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def total_price_cents(self):
        return sum(item.price_cents for item in self.items.all())

    def __str__(self):
        return f"{self.name} — KES {self.total_price_cents() / 100:.2f}"

    class Meta:
        db_table = 'meal_combos'
        ordering = ['name']


class PaymentTransaction(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('failed', 'Failed'),
    ]
    meal_account = models.ForeignKey(
        MealAccount, on_delete=models.CASCADE,
        related_name='transactions'
    )
    amount_cents = models.IntegerField()
    mpesa_reference = models.CharField(max_length=100, blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                              default='pending')
    callback_payload = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.meal_account.student.full_name} — KES {self.amount_cents / 100:.2f} ({self.status})"

    class Meta:
        db_table = 'payment_transactions'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]


class MealDistributionEvent(models.Model):
    meal_account = models.ForeignKey(
        MealAccount, on_delete=models.CASCADE,
        related_name='distribution_events'
    )
    recorded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='recorded_distributions',
        limit_choices_to={'role': 'kitchen'}
    )
    # The specific food items served this time (each carries its own
    # price_cents). amount_cents is the sum at the moment of serving —
    # stored rather than recomputed, so a later price change to a
    # MenuItem doesn't rewrite history.
    items = models.ManyToManyField(MenuItem, blank=True,
                                    related_name='distribution_events')
    amount_cents = models.IntegerField(default=5000)  # KES 50 — pre-menu default
    meal_date = models.DateField()
    meals_served = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    # recorded_by already identifies who served this meal — exposed as
    # name/email via the serializer rather than duplicating those fields
    # here, since recorded_by is the authenticated kitchen account and
    # can't be spoofed the way a free-text name/email could.

    def __str__(self):
        return f"{self.meal_account.student.full_name} — {self.meal_date}"

    class Meta:
        db_table = 'meal_distribution_events'
        indexes = [
            models.Index(fields=['meal_date']),
        ]


class DemandForecast(models.Model):
    school = models.ForeignKey(
        School, on_delete=models.CASCADE,
        related_name='forecasts'
    )
    forecast_date = models.DateField()
    predicted_meals = models.IntegerField()
    predicted_cost_cents = models.IntegerField()
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.school.name} — {self.forecast_date} — {self.predicted_meals} meals"

    class Meta:
        db_table = 'demand_forecasts'
        unique_together = ('school', 'forecast_date')


class AnomalyFlag(models.Model):
    transaction = models.OneToOneField(
        PaymentTransaction, on_delete=models.CASCADE,
        related_name='anomaly_flag'
    )
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_flags',
        limit_choices_to={'role': 'bursar'}
    )
    anomaly_score = models.FloatField()
    flagged_at = models.DateTimeField(auto_now_add=True)
    reviewed = models.BooleanField(default=False)
    review_notes = models.TextField(blank=True, default='')
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Flag — {self.transaction} — score: {self.anomaly_score:.3f}"

    class Meta:
        db_table = 'anomaly_flags'
        indexes = [
            models.Index(fields=['anomaly_score']),
            models.Index(fields=['reviewed']),
        ]


class CreditRequest(models.Model):
    """A parent's request to raise their child's overdraft limit — "let my
    child keep eating on credit up to KES X, I'll pay it off later." An
    admin approving it *raises credit_limit_cents on the MealAccount*; it
    does not add real balance (that still only happens via a real M-Pesa
    payment)."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    meal_account = models.ForeignKey(
        MealAccount, on_delete=models.CASCADE, related_name='credit_requests')
    requested_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='credit_requests',
        limit_choices_to={'role': 'parent'}
    )
    requested_amount_cents = models.IntegerField()
    reason = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                              default='pending')
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_credit_requests',
        limit_choices_to={'role': 'admin'}
    )
    review_notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return (f"{self.requested_by.full_name} — KES "
                f"{self.requested_amount_cents / 100:.2f} ({self.status})")

    class Meta:
        db_table = 'credit_requests'
        indexes = [models.Index(fields=['status'])]


class SupportIssue(models.Model):
    """An issue a parent raises for the school admin to see and resolve —
    a wrong balance, a meal-quality complaint, an app problem, etc."""
    CATEGORY_CHOICES = [
        ('balance', 'Balance / Payment'),
        ('meal_quality', 'Meal Quality'),
        ('technical', 'App / Technical'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    ]
    raised_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='raised_issues',
        limit_choices_to={'role': 'parent'}
    )
    meal_account = models.ForeignKey(
        MealAccount, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='issues'
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES,
                                default='other')
    subject = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                              default='open')
    resolved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='resolved_issues',
        limit_choices_to={'role': 'admin'}
    )
    resolution_notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.subject} — {self.raised_by.full_name} ({self.status})"

    class Meta:
        db_table = 'support_issues'
        indexes = [models.Index(fields=['status'])]


class AdminIssue(models.Model):
    """A report/issue a school admin raises for the Webmasters Kenya
    superadmin team to see and resolve — a platform bug, a billing
    question, a data/reporting problem, a feature request, etc. Mirrors
    SupportIssue (parent -> school admin) one tier up the chain
    (school admin -> superadmin)."""
    CATEGORY_CHOICES = [
        ('technical', 'Technical / Platform Bug'),
        ('billing', 'Billing & Payments'),
        ('feature_request', 'Feature Request'),
        ('data', 'Data / Reporting Issue'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    ]
    raised_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='raised_admin_issues',
        limit_choices_to={'role': 'admin'}
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES,
                                default='other')
    subject = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                              default='open')
    resolved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='resolved_admin_issues',
        limit_choices_to={'role': 'superadmin'}
    )
    resolution_notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.subject} — {self.raised_by.full_name} ({self.status})"

    class Meta:
        db_table = 'admin_issues'
        indexes = [models.Index(fields=['status'])]


class TermSchedule(models.Model):
    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name='terms')
    term_name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    def current_week_number(self):
        from datetime import date
        today = date.today()
        if today < self.start_date or today > self.end_date:
            return 1
        delta = (today - self.start_date).days
        return min((delta // 7) + 1, 13)

    def __str__(self):
        return f"{self.school.name} — {self.term_name}"

    class Meta:
        db_table = 'term_schedules'
