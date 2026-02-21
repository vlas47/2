from django.urls import path

from .views import (
    ComplexListView,
    ComplexPhotoUploadView,
    ComplexPhotoFileView,
    ComplexPhotoDeleteView,
    ComplexPhotoSetMainView,
    ComplexRefreshDataView,
    ComplexFieldUpdateView,
)

app_name = 'complexes'

urlpatterns = [
    path('', ComplexListView.as_view(), name='index'),
    path('refresh/', ComplexRefreshDataView.as_view(), name='refresh'),
    path('<str:slug>/update-field/', ComplexFieldUpdateView.as_view(), name='update_field'),
    path('upload-photo/', ComplexPhotoUploadView.as_view(), name='upload_photo'),
    path('photos/<str:slug>/<str:filename>', ComplexPhotoFileView.as_view(), name='photo'),
    path('photos/<str:slug>/<str:filename>/delete/', ComplexPhotoDeleteView.as_view(), name='photo_delete'),
    path('photos/<str:slug>/<str:filename>/set-main/', ComplexPhotoSetMainView.as_view(), name='photo_set_main'),
]
