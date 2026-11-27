from django.urls import path

from .task_views import (
    TaskArchiveView,
    TaskCancelView,
    TaskCompleteView,
    TaskDetailView,
    TaskListCreateView,
    TaskReopenView,
)

urlpatterns = [
    path('', TaskListCreateView.as_view(), name='crm-task-list'),
    path('<uuid:task_id>/', TaskDetailView.as_view(), name='crm-task-detail'),
    path('<uuid:task_id>/complete/', TaskCompleteView.as_view(), name='crm-task-complete'),
    path('<uuid:task_id>/cancel/', TaskCancelView.as_view(), name='crm-task-cancel'),
    path('<uuid:task_id>/reopen/', TaskReopenView.as_view(), name='crm-task-reopen'),
    path('<uuid:task_id>/archive/', TaskArchiveView.as_view(), name='crm-task-archive'),
]
