from django.contrib import admin
from .models import (School, User, MealAccount, PaymentTransaction,
                     MealDistributionEvent, DemandForecast, AnomalyFlag,
                     TermSchedule, MenuItem, MealCombo, CreditRequest,
                     SupportIssue)

admin.site.register(School)
admin.site.register(User)
admin.site.register(MealAccount)
admin.site.register(PaymentTransaction)
admin.site.register(MealDistributionEvent)
admin.site.register(DemandForecast)
admin.site.register(AnomalyFlag)
admin.site.register(TermSchedule)
admin.site.register(MenuItem)
admin.site.register(MealCombo)
admin.site.register(CreditRequest)
admin.site.register(SupportIssue)
