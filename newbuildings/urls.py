from django.urls import path

from .views import NewBuildingsView

app_name = 'newbuildings'

urlpatterns = [
    path('', NewBuildingsView.as_view(), name='index'),
]
