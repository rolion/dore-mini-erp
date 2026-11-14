from django.urls import path

from .views import (
    AccountActivateView,
    AccountDeactivateView,
    AccountDetailView,
    AccountListCreateView,
    MethodDetailView,
    MethodListView,
)

urlpatterns = [
    path('accounts/', AccountListCreateView.as_view(), name='accounting-account-list'),
    path('accounts/<uuid:account_id>/', AccountDetailView.as_view(), name='accounting-account-detail'),
    path('accounts/<uuid:account_id>/activate/', AccountActivateView.as_view(), name='accounting-account-activate'),
    path('accounts/<uuid:account_id>/deactivate/', AccountDeactivateView.as_view(),
         name='accounting-account-deactivate'),
    path('payment-methods/', MethodListView.as_view(), name='accounting-method-list'),
    path('payment-methods/<str:code>/', MethodDetailView.as_view(), name='accounting-method-detail'),
]
