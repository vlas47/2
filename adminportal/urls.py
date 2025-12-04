from django.urls import path

from .views import AdminDashboardView, StaffLoginView

app_name = 'adminportal'

urlpatterns = [
    path('', AdminDashboardView.as_view(), name='dashboard'),
    path('login/', StaffLoginView.as_view(), name='login'),
]
