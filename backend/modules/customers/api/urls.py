from django.urls import path

from .views import (
    CustomerActivateView,
    CustomerDeactivateView,
    CustomerDetailView,
    CustomerListCreateView,
)

urlpatterns = [
    path('', CustomerListCreateView.as_view(), name='customer-list'),
    path('<uuid:customer_id>/', CustomerDetailView.as_view(), name='customer-detail'),
    path('<uuid:customer_id>/activate/', CustomerActivateView.as_view(), name='customer-activate'),
    path('<uuid:customer_id>/deactivate/', CustomerDeactivateView.as_view(), name='customer-deactivate'),
]
