from django.urls import path

from .views import CountrysideView

app_name = 'countryside'

urlpatterns = [
    path('', CountrysideView.as_view(), name='index'),
]
