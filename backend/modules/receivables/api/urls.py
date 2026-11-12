from django.urls import path

from .views import CommitmentDetailView, ObligationListView, PaymentCreateView

urlpatterns = [
    path('obligations/', ObligationListView.as_view()),
    path('commitments/<str:kind>/<str:number>/', CommitmentDetailView.as_view()),
    path('commitments/<str:kind>/<str:number>/payments/', PaymentCreateView.as_view()),
]
