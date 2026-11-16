from django.urls import path

from .views import (
    AccountActivateView,
    AccountDeactivateView,
    AccountDetailView,
    AccountListCreateView,
    EntryDetailView,
    EntryListView,
    FiscalPeriodCloseView,
    FiscalPeriodDetailView,
    FiscalPeriodListCreateView,
    FiscalPeriodReopenView,
    MethodDetailView,
    MethodListView,
    RegularizationApplyView,
    RegularizationPreviewView,
)

urlpatterns = [
    path('accounts/', AccountListCreateView.as_view(), name='accounting-account-list'),
    path('accounts/<uuid:account_id>/', AccountDetailView.as_view(), name='accounting-account-detail'),
    path('accounts/<uuid:account_id>/activate/', AccountActivateView.as_view(), name='accounting-account-activate'),
    path('accounts/<uuid:account_id>/deactivate/', AccountDeactivateView.as_view(),
         name='accounting-account-deactivate'),
    path('fiscal-periods/', FiscalPeriodListCreateView.as_view(), name='accounting-fiscal-period-list'),
    path('fiscal-periods/<uuid:period_id>/', FiscalPeriodDetailView.as_view(), name='accounting-fiscal-period-detail'),
    path('fiscal-periods/<uuid:period_id>/close/', FiscalPeriodCloseView.as_view(),
         name='accounting-fiscal-period-close'),
    path('fiscal-periods/<uuid:period_id>/reopen/', FiscalPeriodReopenView.as_view(),
         name='accounting-fiscal-period-reopen'),
    path('entries/', EntryListView.as_view(), name='accounting-entry-list'),
    path('entries/<uuid:entry_id>/', EntryDetailView.as_view(), name='accounting-entry-detail'),
    path('regularization/preview/', RegularizationPreviewView.as_view(), name='accounting-regularization-preview'),
    path('regularization/apply/', RegularizationApplyView.as_view(), name='accounting-regularization-apply'),
    path('payment-methods/', MethodListView.as_view(), name='accounting-method-list'),
    path('payment-methods/<str:code>/', MethodDetailView.as_view(), name='accounting-method-detail'),
]
