from django.urls import path

from .views import (
    WarehouseActivateView,
    WarehouseDeactivateView,
    WarehouseDetailView,
    WarehouseListCreateView,
    WarehouseMakeDefaultView,
)

urlpatterns = [
    path('', WarehouseListCreateView.as_view(), name='warehouse-list'),
    path('<uuid:warehouse_id>/', WarehouseDetailView.as_view(), name='warehouse-detail'),
    path('<uuid:warehouse_id>/activate/', WarehouseActivateView.as_view(), name='warehouse-activate'),
    path('<uuid:warehouse_id>/deactivate/', WarehouseDeactivateView.as_view(), name='warehouse-deactivate'),
    path('<uuid:warehouse_id>/make-default/', WarehouseMakeDefaultView.as_view(), name='warehouse-make-default'),
]
