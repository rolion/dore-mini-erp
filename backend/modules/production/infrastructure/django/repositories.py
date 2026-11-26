from uuid import UUID

from django.db import IntegrityError, transaction

from modules.production.domain.recipe import Recipe, RecipeIngredient, RecipeValidationError

from .models import RecipeIngredientModel, RecipeModel


def to_entity(model: RecipeModel) -> Recipe:
    return Recipe(
        id=model.id, name=model.name, result_product_id=model.result_product_id,
        yield_quantity=model.yield_quantity, active=model.active,
        created_at=model.created_at, updated_at=model.updated_at,
        ingredients=[RecipeIngredient(line.product_id, line.unit_id, line.quantity)
                     for line in model.ingredients.all()])


class RecipeList:
    def __init__(self, queryset):
        self.queryset = queryset

    def count(self):
        return self.queryset.count()

    def __len__(self):
        return self.count()

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [to_entity(model) for model in self.queryset[index]]
        return to_entity(self.queryset[index])


class DjangoRecipeRepository:
    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _recipes(self):
        return RecipeModel.objects.filter(company_id=self.company_id).prefetch_related('ingredients')

    def get(self, recipe_id: UUID, *, for_update: bool = False) -> Recipe | None:
        if for_update:
            # Bloquea solo la fila de la receta (no las hijas) y luego lee sus ingredientes.
            RecipeModel.objects.select_for_update().filter(company_id=self.company_id, pk=recipe_id).first()
        model = self._recipes().filter(pk=recipe_id).first()
        return to_entity(model) if model else None

    def name_taken(self, name: str, *, exclude_id: UUID) -> bool:
        return (RecipeModel.objects.filter(company_id=self.company_id, name__iexact=name)
                .exclude(pk=exclude_id).exists())

    def save(self, recipe: Recipe) -> Recipe:
        values = {'name': recipe.name, 'result_product_id': recipe.result_product_id,
                  'yield_quantity': recipe.yield_quantity, 'active': recipe.active}
        try:
            with transaction.atomic():
                model, _ = RecipeModel.objects.update_or_create(
                    company_id=self.company_id, pk=recipe.id, defaults=values)
                model.ingredients.all().delete()
                RecipeIngredientModel.objects.bulk_create([
                    RecipeIngredientModel(recipe=model, product_id=line.product_id, unit_id=line.unit_id,
                                          quantity=line.quantity, position=position)
                    for position, line in enumerate(recipe.ingredients)])
        except IntegrityError as exc:
            if getattr(getattr(exc.__cause__, 'diag', None), 'constraint_name', None) \
                    != 'production_recipe_company_name_unique':
                raise
            raise RecipeValidationError({'name': ['Ya existe una receta con este nombre en tu empresa.']}) from exc
        return to_entity(self._recipes().get(pk=model.pk))

    def list(self, *, search: str = '', status: str = 'active') -> RecipeList:
        queryset = self._recipes().order_by('name', 'id')
        if search:
            queryset = queryset.filter(name__icontains=search)
        if status == 'active':
            queryset = queryset.filter(active=True)
        elif status == 'inactive':
            queryset = queryset.filter(active=False)
        return RecipeList(queryset)
