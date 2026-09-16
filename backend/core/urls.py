from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/payments/', include('payments.urls')),
    path('api/meals/', include('meals.urls')),
    path('api/forecast/', include('forecasting.urls')),
    path('api/anomalies/', include('anomalies.urls')),
    path('api/reports/', include('anomalies.report_urls')),
    path('api/support/', include('accounts.support_urls')),
    path('api/superadmin/', include('accounts.superadmin_urls')),
]
