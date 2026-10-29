from django.urls import path

from .views import (
    SupplierActivateView,
    SupplierDeactivateView,
    SupplierDetailView,
    SupplierListCreateView,
)

urlpatterns = [
    path('', SupplierListCreateView.as_view(), name='supplier-list'),
    path('<uuid:supplier_id>/', SupplierDetailView.as_view(), name='supplier-detail'),
    path('<uuid:supplier_id>/activate/', SupplierActivateView.as_view(), name='supplier-activate'),
    path('<uuid:supplier_id>/deactivate/', SupplierDeactivateView.as_view(), name='supplier-deactivate'),
]
