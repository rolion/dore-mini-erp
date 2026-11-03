from django.urls import path

from .movement_views import MovementValuationListView, ProductCostListView
from .views import AdoptView, ProposalView, CurrentValuationView

urlpatterns = [
    path('', CurrentValuationView.as_view(), name='valuation'),
    path('proposal/', ProposalView.as_view(), name='valuation-proposal'),
    path('adopt/', AdoptView.as_view(), name='valuation-adopt'),
    path('movements/', MovementValuationListView.as_view(), name='valuation-movements'),
    path('costs/', ProductCostListView.as_view(), name='valuation-costs'),
]
