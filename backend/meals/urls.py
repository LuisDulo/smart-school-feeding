from django.urls import path
from .views import (RecordMealView, DailyDistributionLogView,
                    StudentLookupView, MenuItemListCreateView,
                    MenuItemDetailView, ConsumptionHistoryView,
                    MealComboListCreateView, MealComboDetailView,
                    StudentQRDataView)

urlpatterns = [
    path('serve/', RecordMealView.as_view(), name='record-meal'),
    path('log/', DailyDistributionLogView.as_view(), name='distribution-log'),
    path('lookup/', StudentLookupView.as_view(), name='student-lookup'),
    path('menu/', MenuItemListCreateView.as_view(), name='menu-list-create'),
    path('menu/<int:item_id>/', MenuItemDetailView.as_view(), name='menu-detail'),
    path('combos/', MealComboListCreateView.as_view(), name='combo-list-create'),
    path('combos/<int:combo_id>/', MealComboDetailView.as_view(), name='combo-detail'),
    path('consumption/', ConsumptionHistoryView.as_view(), name='consumption-history'),
    path('qr/', StudentQRDataView.as_view(), name='qr-data'),
]
