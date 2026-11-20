from django.urls import path

from . import views

urlpatterns = [
    path('sales/', views.RunListCreateView.as_view(), name='import-sales-list'),
    path('sales/template/', views.TemplateView.as_view(), name='import-sales-template'),
    path('sales/<str:run_id>/', views.RunDetailView.as_view(), name='import-sales-detail'),
    path('sales/<str:run_id>/preview/', views.RunPreviewView.as_view(), name='import-sales-preview'),
    path('sales/<str:run_id>/execute/', views.RunExecuteView.as_view(), name='import-sales-execute'),
    path('sales/<str:run_id>/rows/', views.RunRowsView.as_view(), name='import-sales-rows'),
]
