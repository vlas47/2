from django.urls import path

from .views import AdminDashboardView, StaffLoginView, ManagerCabinetView

app_name = 'adminportal'

urlpatterns = [
    path('', AdminDashboardView.as_view(), name='dashboard'),
    path('login/', StaffLoginView.as_view(), name='login'),
    path('manager/', ManagerCabinetView.as_view(), name='manager'),
]
