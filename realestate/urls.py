from django.urls import path

from .views import RealEstateDashboardView

app_name = 'realestate'

urlpatterns = [
    path('', RealEstateDashboardView.as_view(), name='dashboard'),
]
