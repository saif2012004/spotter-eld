from rest_framework import serializers


class PlanTripRequestSerializer(serializers.Serializer):
    current_location = serializers.CharField(max_length=255)
    pickup_location  = serializers.CharField(max_length=255)
    dropoff_location = serializers.CharField(max_length=255)
    cycle_used_hours = serializers.FloatField(min_value=0.0, max_value=70.0)
    # Optional — defaults to now() in the view
    start_time       = serializers.DateTimeField(required=False, allow_null=True, default=None)
