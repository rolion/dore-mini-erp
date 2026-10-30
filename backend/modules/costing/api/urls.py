from django.urls import path

from .views import AdoptView, ProposalView, CurrentValuationView

urlpatterns = [
    path('', CurrentValuationView.as_view(), name='valuation'),
    path('proposal/', ProposalView.as_view(), name='valuation-proposal'),
    path('adopt/', AdoptView.as_view(), name='valuation-adopt'),
]
