from django.urls import path

from .views import ProformaActionView, ProformaDetailView, ProformaListCreateView

urlpatterns = [
    path('proformas/', ProformaListCreateView.as_view()),
    path('proformas/<uuid:proforma_id>/', ProformaDetailView.as_view()),
    path('proformas/<uuid:proforma_id>/present/', ProformaActionView.as_view(action='present')),
    path('proformas/<uuid:proforma_id>/new-version/', ProformaActionView.as_view(action='new_version')),
]
