from django.urls import path

from .views import (
    DashboardView,
    ExpensesReportView,
    PendingView,
    SalesByChannelView,
    SalesReportView,
    TopCustomersView,
    TopProductsView,
)

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='report-dashboard'),
    path('sales/', SalesReportView.as_view(), name='report-sales'),
    path('expenses/', ExpensesReportView.as_view(), name='report-expenses'),
    path('sales-by-channel/', SalesByChannelView.as_view(), name='report-sales-by-channel'),
    path('top-products/', TopProductsView.as_view(), name='report-top-products'),
    path('top-customers/', TopCustomersView.as_view(), name='report-top-customers'),
    path('pending/', PendingView.as_view(), name='report-pending'),
]
