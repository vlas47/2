from django.urls import path

from .views import SecondaryView

app_name = 'secondary'

urlpatterns = [
    path('', SecondaryView.as_view(), name='index'),
]
