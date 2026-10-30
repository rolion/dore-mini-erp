from django.contrib import admin
from django.urls import include, path

from modules.expenses.api.urls import category_urlpatterns, expense_urlpatterns

from .health import health

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health, name='health'),
    path('api/auth/', include('modules.accounts.api.urls')),
    path('api/products/', include('modules.catalog.api.urls')),
    path('api/units/', include('modules.catalog.api.unit_urls')),
    path('api/warehouses/', include('modules.inventory.api.urls')),
    path('api/stock-movements/', include('modules.inventory.api.movement_urls')),
    path('api/stock/', include('modules.inventory.api.stock_urls')),
    path('api/stock-adjustments/', include('modules.inventory.api.adjustment_urls')),
    path('api/customers/', include('modules.customers.api.urls')),
    path('api/suppliers/', include('modules.purchases.api.urls')),
    path('api/purchases/', include('modules.purchases.api.purchase_urls')),
    path('api/orders/', include('modules.sales.api.urls')),
    path('api/expenses/', include(expense_urlpatterns)),
    path('api/expense-categories/', include(category_urlpatterns)),
    path('api/reports/', include('modules.reporting.api.urls')),
    path('api/modules/', include('modules.modularity.api.urls')),
    path('api/settings/', include('modules.modularity.api.settings_urls')),
]
