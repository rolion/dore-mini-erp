from django.urls import path

from .lead_views import LeadConvertView, LeadDetailView, LeadListCreateView

urlpatterns = [
    path('', LeadListCreateView.as_view(), name='crm-lead-list'),
    path('<uuid:lead_id>/', LeadDetailView.as_view(), name='crm-lead-detail'),
    path('<uuid:lead_id>/convert/', LeadConvertView.as_view(), name='crm-lead-convert'),
]
