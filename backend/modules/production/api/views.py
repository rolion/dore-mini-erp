from django.db import transaction
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.production.application.recipes import RecipeBook
from modules.production.domain.recipe import RecipeIngredient, RecipeNotFound, RecipeValidationError
from modules.production.infrastructure.adapters import CatalogProducts
from modules.production.infrastructure.django.repositories import DjangoRecipeRepository
from shared.tenancy import company_id_from

from .serializers import RecipeInputSerializer

STATUSES = ('active', 'inactive', 'all')


class RecipePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        for name in ('page', 'page_size'):
            raw = request.query_params.get(name)
            if raw is not None and (len(raw) > 10 or not raw.isascii() or not raw.isdigit() or int(raw) < 1):
                raise ValidationError({name: ['Ingresa un entero mayor que cero.']})
        try:
            return super().paginate_queryset(queryset, request, view=view)
        except NotFound as exc:
            raise ValidationError({'page': ['La página solicitada ya no está disponible.']}) from exc


def _book(request) -> RecipeBook:
    company_id = company_id_from(request)
    return RecipeBook(DjangoRecipeRepository(company_id), CatalogProducts(company_id))


def _unit(product):
    if product is None or product.unit_id is None:
        return None
    return {'id': product.unit_id, 'abbreviation': product.unit_abbreviation}


def _serialize(request, recipes: list) -> list[dict]:
    """Detalle de cada receta con los datos vigentes de sus productos (una sola consulta a Catálogo)."""
    ids = {recipe.result_product_id for recipe in recipes}
    ids.update(line.product_id for recipe in recipes for line in recipe.ingredients)
    products = CatalogProducts(company_id_from(request)).products(ids)
    rows = []
    for recipe in recipes:
        result = products.get(recipe.result_product_id)
        rows.append({
            'id': recipe.id,
            'name': recipe.name,
            'result_product': {'id': recipe.result_product_id, 'name': result.name if result else None,
                               'active': result.active if result else False, 'unit': _unit(result)},
            'yield_quantity': f'{recipe.yield_quantity:.4f}',
            'ingredients': [{
                'product_id': line.product_id,
                'product_name': products[line.product_id].name if line.product_id in products else None,
                'product_active': products[line.product_id].active if line.product_id in products else False,
                'unit_id': line.unit_id,
                'unit_abbreviation': (products[line.product_id].unit_abbreviation
                                      if line.product_id in products else None),
                'quantity': f'{line.quantity:.4f}',
            } for line in recipe.ingredients],
            'active': recipe.active,
            'created_at': recipe.created_at,
            'updated_at': recipe.updated_at,
        })
    return rows


def _values(request) -> dict:
    serializer = RecipeInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    return {
        'name': data['name'], 'result_product_id': data['result_product_id'],
        'yield_quantity': data['yield_quantity'],
        'ingredients': [RecipeIngredient(line['product_id'], line.get('unit_id'), line['quantity'])
                        for line in data['ingredients']],
    }


def _run(request, callback, **values):
    try:
        with transaction.atomic():
            recipe = callback(**values)
        return _serialize(request, [recipe])[0]
    except RecipeNotFound as exc:
        raise NotFound('Receta no encontrada.') from exc
    except RecipeValidationError as exc:
        raise ValidationError(exc.errors) from exc


class RecipeListCreateView(APIView):
    required_modules = ('production',)

    def get(self, request):
        status = request.query_params.get('status', 'active')
        if status not in STATUSES:
            raise ValidationError({'status': ['Usa active, inactive o all.']})
        recipes = _book(request).repository.list(search=request.query_params.get('q', '').strip(), status=status)
        paginator = RecipePagination()
        page = paginator.paginate_queryset(recipes, request, view=self)
        return paginator.get_paginated_response(_serialize(request, page))

    def post(self, request):
        return Response(_run(request, _book(request).create, **_values(request)), status=201)


class RecipeDetailView(APIView):
    required_modules = ('production',)
    http_method_names = ['get', 'put', 'head', 'options']

    def get(self, request, recipe_id):
        return Response(_run(request, _book(request).get, recipe_id=recipe_id))

    def put(self, request, recipe_id):
        return Response(_run(request, _book(request).update, recipe_id=recipe_id, **_values(request)))


class RecipeActivateView(APIView):
    required_modules = ('production',)
    active = True

    def post(self, request, recipe_id):
        return Response(_run(request, _book(request).set_active, recipe_id=recipe_id, active=self.active))


class RecipeDeactivateView(RecipeActivateView):
    active = False
