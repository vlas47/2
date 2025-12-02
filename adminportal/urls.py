from django.urls import path

from .views import AdminDashboardView

app_name = 'adminportal'

urlpatterns = [
    path('', AdminDashboardView.as_view(), name='dashboard'),
]
