from django.urls import path

from .views import (
    ProformaActionView, ProformaDecisionView, ProformaDetailView, ProformaListCreateView, ProformaPrintableView,
    ProformaRectifyView,
)

urlpatterns = [
    path('proformas/', ProformaListCreateView.as_view()),
    path('proformas/<uuid:proforma_id>/', ProformaDetailView.as_view()),
    path('proformas/<uuid:proforma_id>/present/', ProformaActionView.as_view(action='present')),
    path('proformas/<uuid:proforma_id>/new-version/', ProformaActionView.as_view(action='new_version')),
    path('proformas/<uuid:proforma_id>/decisions/', ProformaDecisionView.as_view()),
    path('proformas/<uuid:proforma_id>/lines/<uuid:line_id>/rectify/', ProformaRectifyView.as_view()),
    path('proformas/<uuid:proforma_id>/printable/', ProformaPrintableView.as_view()),
]
