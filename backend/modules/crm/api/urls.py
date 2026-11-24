from django.urls import include, path

from .views import CrmCustomerListView

urlpatterns = [
    path('customers/', CrmCustomerListView.as_view(), name='crm-customer-list'),
    path('leads/', include('modules.crm.api.lead_urls')),
    path('opportunities/', include('modules.crm.api.opportunity_urls')),
]
