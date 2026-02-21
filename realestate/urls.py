from django.urls import path

from .views import (
    CleanDuplicatesView,
    CleanPhotosView,
    ImportSetlView,
    RealEstateCardsView,
    RealEstateDashboardView,
)

app_name = 'realestate'

urlpatterns = [
    path('', RealEstateDashboardView.as_view(), name='dashboard'),
    path('cards/', RealEstateCardsView.as_view(), name='cards'),
    path('clean-photos/', CleanPhotosView.as_view(), name='clean_photos'),
    path('clean-duplicates/', CleanDuplicatesView.as_view(), name='clean_duplicates'),
    path('import-setl/', ImportSetlView.as_view(), name='import_setl'),
]
