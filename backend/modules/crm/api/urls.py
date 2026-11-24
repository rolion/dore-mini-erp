from django.urls import path

from .views import CrmCustomerListView

urlpatterns = [
    path('customers/', CrmCustomerListView.as_view(), name='crm-customer-list'),
]
