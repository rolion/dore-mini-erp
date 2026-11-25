from django.urls import include, path

from .views import CrmCustomerListView, CrmUserListView

urlpatterns = [
    path('customers/', CrmCustomerListView.as_view(), name='crm-customer-list'),
    path('users/', CrmUserListView.as_view(), name='crm-user-list'),
    path('leads/', include('modules.crm.api.lead_urls')),
    path('opportunities/', include('modules.crm.api.opportunity_urls')),
]
