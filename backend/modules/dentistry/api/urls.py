from django.urls import path
from .views import CapabilitiesView, PatientListView, PatientDetailView, PatientStateView, PatientHistoryView

urlpatterns = [
    path('capabilities/', CapabilitiesView.as_view()),
    path('patients/', PatientListView.as_view()),
    path('patients/<uuid:customer_id>/', PatientDetailView.as_view()),
    path('patients/<uuid:customer_id>/archive/', PatientStateView.as_view(action='archive')),
    path('patients/<uuid:customer_id>/activate/', PatientStateView.as_view(action='activate')),
    path('patients/<uuid:customer_id>/history/', PatientHistoryView.as_view()),
]
