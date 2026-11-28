from django.urls import path

from .inbox_views import (
    ConversationContactView,
    ConversationDetailView,
    ConversationLinkableOpportunitiesView,
    ConversationListView,
    ConversationOpportunityView,
    ConversationOwnerView,
    MessageListCreateView,
    MessageRetryView,
)

urlpatterns = [
    path('conversations/', ConversationListView.as_view(), name='crm-inbox-list'),
    path('conversations/<uuid:conversation_id>/', ConversationDetailView.as_view(), name='crm-inbox-detail'),
    path('conversations/<uuid:conversation_id>/messages/', MessageListCreateView.as_view(),
         name='crm-inbox-messages'),
    path('conversations/<uuid:conversation_id>/messages/<uuid:message_id>/retry/', MessageRetryView.as_view(),
         name='crm-inbox-message-retry'),
    path('conversations/<uuid:conversation_id>/owner/', ConversationOwnerView.as_view(), name='crm-inbox-owner'),
    path('conversations/<uuid:conversation_id>/contact/', ConversationContactView.as_view(),
         name='crm-inbox-contact'),
    path('conversations/<uuid:conversation_id>/opportunity/', ConversationOpportunityView.as_view(),
         name='crm-inbox-opportunity'),
    path('conversations/<uuid:conversation_id>/opportunities/', ConversationLinkableOpportunitiesView.as_view(),
         name='crm-inbox-opportunities'),
]
