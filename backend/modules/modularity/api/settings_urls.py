from django.urls import path

from .settings_views import ModuleSettingsView, SettingChangeListView

urlpatterns = [
    path('<str:module>/', ModuleSettingsView.as_view(), name='module-settings'),
    path('<str:scope>/history/', SettingChangeListView.as_view(), name='module-settings-history'),
]
