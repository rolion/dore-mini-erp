from django.urls import path

from .views import RecipeActivateView, RecipeDeactivateView, RecipeDetailView, RecipeListCreateView

urlpatterns = [
    path('', RecipeListCreateView.as_view(), name='recipe-list'),
    path('<uuid:recipe_id>/', RecipeDetailView.as_view(), name='recipe-detail'),
    path('<uuid:recipe_id>/activate/', RecipeActivateView.as_view(), name='recipe-activate'),
    path('<uuid:recipe_id>/deactivate/', RecipeDeactivateView.as_view(), name='recipe-deactivate'),
]
