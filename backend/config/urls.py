from django.contrib import admin
from django.urls import include, path

from modules.expenses.api.urls import category_urlpatterns, expense_urlpatterns

from .health import health

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health, name='health'),
    path('api/auth/', include('modules.accounts.api.urls')),
    path('api/products/', include('modules.catalog.api.urls')),
    path('api/customers/', include('modules.customers.api.urls')),
    path('api/orders/', include('modules.sales.api.urls')),
    path('api/expenses/', include(expense_urlpatterns)),
    path('api/expense-categories/', include(category_urlpatterns)),
    path('api/reports/', include('modules.reporting.api.urls')),
]
