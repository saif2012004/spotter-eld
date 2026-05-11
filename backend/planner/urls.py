from django.urls import path

from planner.views import plan_trip_view

urlpatterns = [
    path("plan-trip/", plan_trip_view, name="plan-trip"),
]
