import uuid

from django.db import models
from django.db.models.functions import Lower


class RecipeModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=150)
    # Referencias a otro módulo (Catálogo): UUID sin FK.
    result_product_id = models.UUIDField()
    yield_quantity = models.DecimalField(max_digits=14, decimal_places=4)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'production_recipe'
        ordering = ['name', 'id']
        constraints = [
            models.UniqueConstraint(Lower('name'), 'company_id', name='production_recipe_company_name_unique'),
            models.CheckConstraint(condition=models.Q(yield_quantity__gt=0), name='production_recipe_yield_positive'),
        ]


class RecipeIngredientModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipe = models.ForeignKey(RecipeModel, on_delete=models.CASCADE, related_name='ingredients')
    product_id = models.UUIDField()
    unit_id = models.UUIDField(null=True, blank=True)
    quantity = models.DecimalField(max_digits=14, decimal_places=4)
    position = models.PositiveIntegerField()

    class Meta:
        db_table = 'production_recipe_ingredient'
        ordering = ['position']
        constraints = [
            models.UniqueConstraint(fields=['recipe', 'product_id'], name='production_ingredient_product_unique'),
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name='production_ingredient_quantity_positive'),
        ]
