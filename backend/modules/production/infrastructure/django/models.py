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


class ProductionOrderModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    number = models.PositiveIntegerField()
    status = models.CharField(max_length=20, default='draft')
    # Copia de la receta al crear (sin FK: la orden no depende de ella después).
    recipe_id = models.UUIDField()
    recipe_name = models.CharField(max_length=150)
    result_product_id = models.UUIDField()
    result_product_name = models.CharField(max_length=200)
    result_unit_id = models.UUIDField(null=True, blank=True)
    result_unit_abbreviation = models.CharField(max_length=20, null=True, blank=True)
    yield_per_preparation = models.DecimalField(max_digits=14, decimal_places=4)
    # Referencia a Inventario: UUID sin FK.
    warehouse_id = models.UUIDField()
    preparations = models.PositiveIntegerField()
    started_at = models.DateTimeField(null=True, blank=True)
    # Registro de producción al pasar a refrigeración (lote por id y código, sin FK a Inventario).
    actual_output = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True)
    entered_at = models.DateTimeField(null=True, blank=True)
    refrigerated_at = models.DateTimeField(null=True, blank=True)
    lot_id = models.UUIDField(null=True, blank=True)
    lot_code = models.CharField(max_length=30, blank=True, default='')
    cost_total = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    # Liberación del lote (TASK-liberar-lote-despues-refrigeracion).
    released_at = models.DateTimeField(null=True, blank=True)
    released_by_id = models.UUIDField(null=True, blank=True)
    released_by_name = models.CharField(max_length=150, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'production_order'
        ordering = ['-number']
        constraints = [
            models.UniqueConstraint(fields=['company_id', 'number'], name='production_order_number_unique'),
            models.CheckConstraint(condition=models.Q(preparations__gt=0), name='production_order_preparations_gt_0'),
            models.CheckConstraint(
                condition=(models.Q(status='draft', started_at__isnull=True)
                           | models.Q(status='in_preparation', started_at__isnull=False)
                           | models.Q(status='refrigerating', started_at__isnull=False, lot_id__isnull=False,
                                      actual_output__isnull=False, entered_at__isnull=False)
                           | models.Q(status='ready_to_pack', started_at__isnull=False, lot_id__isnull=False,
                                      actual_output__isnull=False, entered_at__isnull=False,
                                      released_at__isnull=False)),
                name='production_order_started_with_status'),
        ]


class ProductionOrderIngredientModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(ProductionOrderModel, on_delete=models.CASCADE, related_name='ingredients')
    product_id = models.UUIDField()
    product_name = models.CharField(max_length=200)
    unit_id = models.UUIDField(null=True, blank=True)
    unit_abbreviation = models.CharField(max_length=20, null=True, blank=True)
    quantity_per_preparation = models.DecimalField(max_digits=14, decimal_places=4)
    actual_quantity = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True)
    position = models.PositiveIntegerField()

    class Meta:
        db_table = 'production_order_ingredient'
        ordering = ['position']


class ProductionOrderCounterModel(models.Model):
    company_id = models.UUIDField(unique=True, db_index=True)
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'production_order_counter'


class PackingModel(models.Model):
    """Tanda de empaque de una orden (TASK-empacar-bolsas-de-6-venta-detalle); inmutable."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    order = models.ForeignKey(ProductionOrderModel, on_delete=models.PROTECT, related_name='packings')
    number = models.PositiveIntegerField()
    request_id = models.UUIDField()
    packs = models.PositiveIntegerField()
    # Referencias a Catálogo e Inventario: UUID sin FK.
    pack_product_id = models.UUIDField()
    pack_product_name = models.CharField(max_length=200)
    bag_product_id = models.UUIDField()
    bag_product_name = models.CharField(max_length=200)
    bulk_quantity = models.DecimalField(max_digits=16, decimal_places=4)
    bags_quantity = models.DecimalField(max_digits=16, decimal_places=4)
    bag_per_pack = models.DecimalField(max_digits=10, decimal_places=4, default=1)
    label_product_id = models.UUIDField(null=True, blank=True)
    label_product_name = models.CharField(max_length=200, blank=True, default='')
    labels_quantity = models.DecimalField(max_digits=16, decimal_places=4, default=0)
    lot_id = models.UUIDField()
    lot_code = models.CharField(max_length=30)
    cost_total = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    unit_cost = models.DecimalField(max_digits=14, decimal_places=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by_id = models.UUIDField(null=True, blank=True)
    created_by_name = models.CharField(max_length=150, blank=True, default='')

    class Meta:
        db_table = 'production_packing'
        ordering = ['number']
        constraints = [
            models.UniqueConstraint(fields=['order', 'request_id'], name='production_packing_request_unique'),
            models.UniqueConstraint(fields=['order', 'number'], name='production_packing_number_unique'),
            models.CheckConstraint(condition=models.Q(packs__gt=0), name='production_packing_packs_gt_0'),
        ]
