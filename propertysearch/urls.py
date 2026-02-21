from django.urls import path

from .views import PropertySearchView, PropertyComplexListView, PropertyComplexDetailView

app_name = 'propertysearch'

urlpatterns = [
    path('', PropertySearchView.as_view(), name='index'),
    path('complexes/', PropertyComplexListView.as_view(), name='complexes'),
    path('complexes/<str:slug>/', PropertyComplexDetailView.as_view(), name='complex_detail'),
]
