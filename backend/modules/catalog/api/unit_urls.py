from django.urls import path

from .unit_views import UnitActivateView, UnitDeactivateView, UnitDetailView, UnitListCreateView

urlpatterns = [
    path('', UnitListCreateView.as_view(), name='unit-list'),
    path('<uuid:unit_id>/', UnitDetailView.as_view(), name='unit-detail'),
    path('<uuid:unit_id>/activate/', UnitActivateView.as_view(), name='unit-activate'),
    path('<uuid:unit_id>/deactivate/', UnitDeactivateView.as_view(), name='unit-deactivate'),
]
