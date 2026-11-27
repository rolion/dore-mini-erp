from django.urls import path

from .task_views import ActivityListCreateView

urlpatterns = [path('', ActivityListCreateView.as_view(), name='crm-activity-list')]
