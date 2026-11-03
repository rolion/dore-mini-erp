from django.urls import path

from .views import ServiceActivateView, ServiceDeactivateView, ServiceDetailView, ServiceListCreateView

urlpatterns = [
    path('', ServiceListCreateView.as_view(), name='service-list'),
    path('<uuid:service_id>/', ServiceDetailView.as_view(), name='service-detail'),
    path('<uuid:service_id>/activate/', ServiceActivateView.as_view(), name='service-activate'),
    path('<uuid:service_id>/deactivate/', ServiceDeactivateView.as_view(), name='service-deactivate'),
]
