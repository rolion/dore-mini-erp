from django.urls import include, path

from .views import CrmCustomerListView, CrmUserListView

urlpatterns = [
    path('customers/', CrmCustomerListView.as_view(), name='crm-customer-list'),
    path('users/', CrmUserListView.as_view(), name='crm-user-list'),
    path('leads/', include('modules.crm.api.lead_urls')),
    path('opportunities/', include('modules.crm.api.opportunity_urls')),
    path('tasks/', include('modules.crm.api.task_urls')),
    path('activities/', include('modules.crm.api.activity_urls')),
    path('inbox/', include('modules.crm.api.inbox_urls')),
]
