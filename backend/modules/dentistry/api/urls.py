from django.urls import path
from .proforma_views import (
    PatientProformaListCreateView, ProformaActionView, ProformaDecisionView, ProformaDetailView,
    ProformaPrintableView, ProformaRectifyView,
)
from .proforma_report_views import (
    PaidProformasReportExportView, PaidProformasReportView, ReceivableProformasReportExportView,
    ReceivableProformasReportView,
)
from .evaluation_views import (
    CatalogView, EvaluationAmendView, EvaluationConfirmView, EvaluationDetailView, PatientEvaluationListView,
)
from .encounter_views import (
    AppointmentEncounterView, AppointmentListView, EncounterActionView, EncounterDetailView,
    EncounterOdontogramView, PatientEncounterListView,
)
from .views import CapabilitiesView, PatientListView, PatientDetailView, PatientStateView, PatientHistoryView

urlpatterns = [
    path('capabilities/', CapabilitiesView.as_view()),
    path('odontogram/catalog/', CatalogView.as_view()),
    path('patients/<uuid:customer_id>/evaluations/', PatientEvaluationListView.as_view()),
    path('evaluations/<uuid:evaluation_id>/', EvaluationDetailView.as_view()),
    path('evaluations/<uuid:evaluation_id>/confirm/', EvaluationConfirmView.as_view()),
    path('evaluations/<uuid:evaluation_id>/amend/', EvaluationAmendView.as_view()),
    path('appointments/', AppointmentListView.as_view()),
    path('appointments/<uuid:appointment_id>/encounter/', AppointmentEncounterView.as_view()),
    path('appointments/<uuid:appointment_id>/encounter/start/', EncounterActionView.as_view(action='start')),
    path('appointments/<uuid:appointment_id>/encounter/finish/', EncounterActionView.as_view(action='finish')),
    path('appointments/<uuid:appointment_id>/encounter/cancel/', EncounterActionView.as_view(action='cancel')),
    path('encounters/<uuid:encounter_id>/', EncounterDetailView.as_view()),
    path('encounters/<uuid:encounter_id>/odontogram/', EncounterOdontogramView.as_view()),
    path('patients/<uuid:customer_id>/encounters/', PatientEncounterListView.as_view()),
    path('patients/', PatientListView.as_view()),
    path('patients/<uuid:customer_id>/', PatientDetailView.as_view()),
    path('patients/<uuid:customer_id>/archive/', PatientStateView.as_view(action='archive')),
    path('patients/<uuid:customer_id>/activate/', PatientStateView.as_view(action='activate')),
    path('patients/<uuid:customer_id>/history/', PatientHistoryView.as_view()),
    path('patients/<uuid:customer_id>/proformas/', PatientProformaListCreateView.as_view()),
    path('proformas/<uuid:proforma_id>/', ProformaDetailView.as_view()),
    path('proformas/<uuid:proforma_id>/present/', ProformaActionView.as_view(action='present')),
    path('proformas/<uuid:proforma_id>/new-version/', ProformaActionView.as_view(action='new_version')),
    path('proformas/<uuid:proforma_id>/decisions/', ProformaDecisionView.as_view()),
    path('proformas/<uuid:proforma_id>/lines/<uuid:line_id>/rectify/', ProformaRectifyView.as_view()),
    path('proformas/<uuid:proforma_id>/printable/', ProformaPrintableView.as_view()),
    path('reports/proformas/receivable/', ReceivableProformasReportView.as_view()),
    path('reports/proformas/receivable/export/<str:file_format>/', ReceivableProformasReportExportView.as_view()),
    path('reports/proformas/paid/', PaidProformasReportView.as_view()),
    path('reports/proformas/paid/export/<str:file_format>/', PaidProformasReportExportView.as_view()),
]
