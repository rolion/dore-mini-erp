from django.urls import path

from .opportunity_views import (
    OpportunityCloseView,
    OpportunityDetailView,
    OpportunityHistoryView,
    OpportunityLinkableOrdersView,
    OpportunityListCreateView,
    OpportunityMoveView,
    OpportunityOrderView,
)

urlpatterns = [
    path('', OpportunityListCreateView.as_view(), name='crm-opportunity-list'),
    path('<uuid:opportunity_id>/', OpportunityDetailView.as_view(), name='crm-opportunity-detail'),
    path('<uuid:opportunity_id>/move/', OpportunityMoveView.as_view(), name='crm-opportunity-move'),
    path('<uuid:opportunity_id>/close/', OpportunityCloseView.as_view(), name='crm-opportunity-close'),
    path('<uuid:opportunity_id>/order/', OpportunityOrderView.as_view(), name='crm-opportunity-order'),
    path('<uuid:opportunity_id>/orders/', OpportunityLinkableOrdersView.as_view(), name='crm-opportunity-orders'),
    path('<uuid:opportunity_id>/history/', OpportunityHistoryView.as_view(), name='crm-opportunity-history'),
]
