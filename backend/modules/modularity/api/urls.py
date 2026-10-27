from django.urls import path

from .views import ModuleDisableView, ModuleEnableView, ModuleListView

urlpatterns = [
    path('', ModuleListView.as_view(), name='module-list'),
    path('<str:key>/enable/', ModuleEnableView.as_view(), name='module-enable'),
    path('<str:key>/disable/', ModuleDisableView.as_view(), name='module-disable'),
]
