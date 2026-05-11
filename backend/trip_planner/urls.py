from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include


def api_root(request):
    return JsonResponse({
        "service": "Spotter ELD API",
        "status": "running",
        "endpoints": ["/api/plan-trip/"],
    })


urlpatterns = [
    path('', api_root),
    path('admin/', admin.site.urls),
    path('api/', include('planner.urls')),
]
