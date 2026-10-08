from django.contrib import admin
from django.urls import include, path

from .health import health

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health, name='health'),
    path('api/auth/', include('modules.accounts.api.urls')),
    path('api/products/', include('modules.catalog.api.urls')),
    path('api/customers/', include('modules.customers.api.urls')),
]
