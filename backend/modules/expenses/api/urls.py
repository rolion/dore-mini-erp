from django.urls import path

from .views import (
    CategoryActivateView,
    CategoryDeactivateView,
    CategoryDetailView,
    CategoryListCreateView,
    ExpenseDetailView,
    ExpenseListCreateView,
    ExpenseVoidView,
)

# Los ids van como `str` y la vista los convierte: un id mal formado responde 404 `{detail}`, no una página HTML.
expense_urlpatterns = [
    path('', ExpenseListCreateView.as_view(), name='expense-list'),
    path('<str:expense_id>/', ExpenseDetailView.as_view(), name='expense-detail'),
    path('<str:expense_id>/void/', ExpenseVoidView.as_view(), name='expense-void'),
]

category_urlpatterns = [
    path('', CategoryListCreateView.as_view(), name='expense-category-list'),
    path('<str:category_id>/', CategoryDetailView.as_view(), name='expense-category-detail'),
    path('<str:category_id>/activate/', CategoryActivateView.as_view(), name='expense-category-activate'),
    path('<str:category_id>/deactivate/', CategoryDeactivateView.as_view(), name='expense-category-deactivate'),
]
