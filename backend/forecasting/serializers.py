from rest_framework import serializers
from meals.models import DemandForecast


class DemandForecastSerializer(serializers.ModelSerializer):
    forecast_date_str = serializers.DateField(
        source='forecast_date', format='%Y-%m-%d', read_only=True)
    predicted_cost_ksh = serializers.SerializerMethodField()
    school_name = serializers.CharField(
        source='school.name', read_only=True)

    class Meta:
        model = DemandForecast
        fields = ['id', 'school_name', 'forecast_date',
                  'forecast_date_str', 'predicted_meals',
                  'predicted_cost_cents', 'predicted_cost_ksh',
                  'generated_at']

    def get_predicted_cost_ksh(self, obj):
        return obj.predicted_cost_cents / 100
