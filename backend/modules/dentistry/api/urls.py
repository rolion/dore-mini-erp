from django.urls import path
from .proforma_views import (
    PatientProformaListCreateView, ProformaActionView, ProformaDetailView,
)
from .views import CapabilitiesView, PatientListView, PatientDetailView, PatientStateView, PatientHistoryView

urlpatterns = [
    path('capabilities/', CapabilitiesView.as_view()),
    path('patients/', PatientListView.as_view()),
    path('patients/<uuid:customer_id>/', PatientDetailView.as_view()),
    path('patients/<uuid:customer_id>/archive/', PatientStateView.as_view(action='archive')),
    path('patients/<uuid:customer_id>/activate/', PatientStateView.as_view(action='activate')),
    path('patients/<uuid:customer_id>/history/', PatientHistoryView.as_view()),
    path('patients/<uuid:customer_id>/proformas/', PatientProformaListCreateView.as_view()),
    path('proformas/<uuid:proforma_id>/', ProformaDetailView.as_view()),
    path('proformas/<uuid:proforma_id>/present/', ProformaActionView.as_view(action='present')),
    path('proformas/<uuid:proforma_id>/new-version/', ProformaActionView.as_view(action='new_version')),
]
