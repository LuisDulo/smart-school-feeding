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
    balance_cents = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.full_name} — KES {self.balance_cents / 100:.2f}"

    def get_balance_ksh(self):
        return self.balance_cents / 100

    def is_low_balance(self):
        return self.balance_cents < 10000  # below KES 100

    class Meta:
        db_table = 'meal_accounts'


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
    meal_date = models.DateField()
    meals_served = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

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
