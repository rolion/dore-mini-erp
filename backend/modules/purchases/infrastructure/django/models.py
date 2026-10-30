import uuid

from django.db import models


class SupplierModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Empresa propietaria; solo UUID, sin FK (los módulos no acoplan modelos ni migraciones).
    company_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=150)
    tax_id = models.CharField(max_length=50, blank=True, default='')
    phone = models.CharField(max_length=30, blank=True, default='')
    email = models.CharField(max_length=254, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'purchases_supplier'
        ordering = ['name', 'id']
        indexes = [models.Index(fields=['company_id', 'active'], name='purch_supplier_company_active')]


class PurchaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Empresa propietaria; solo UUID, sin FK. Las líneas heredan la empresa de su compra.
    company_id = models.UUIDField(db_index=True)
    # Mismo contexto, pero se referencia por UUID como el resto de agregados (sin FK entre agregados).
    supplier_id = models.UUIDField()
    purchase_date = models.DateField()
    external_reference = models.CharField(max_length=100, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, default='draft')
    # Derivado: solo lo escribe el repositorio a partir del agregado.
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True, default='')
    reception_status = models.CharField(max_length=20, default='not_received')
    payment_status = models.CharField(max_length=20, default='unpaid')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'purchases_purchase'
        ordering = ['-purchase_date', '-created_at', 'id']
        indexes = [
            models.Index(fields=['company_id', 'purchase_date'], name='purch_purch_company_date'),
            models.Index(fields=['company_id', 'supplier_id'], name='purch_purch_company_supplier'),
        ]


class PurchaseItemModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchase = models.ForeignKey(PurchaseModel, on_delete=models.CASCADE, related_name='items')
    position = models.PositiveIntegerField()
    # Producto de Catálogo: solo UUID, sin FK (los módulos no acoplan modelos ni migraciones).
    product_id = models.UUIDField()
    product_name = models.CharField(max_length=150)
    unit_abbreviation = models.CharField(max_length=10, blank=True, default='')
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    # Derivado: solo lo escribe el repositorio.
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'purchases_purchase_item'
        ordering = ['position']


class ReceiptModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    # Compra del mismo contexto: por UUID, sin FK (la compra recrea sus líneas al guardar).
    purchase_id = models.UUIDField()
    receipt_date = models.DateField()
    status = models.CharField(max_length=20, default='confirmed')
    # Almacén de Inventario (solo UUID): únicamente si la recepción generó entradas de stock.
    warehouse_id = models.UUIDField(null=True, blank=True)
    # Modo con que se confirmó ('inventory' | 'documental'); nulo en recepciones anteriores sin almacén.
    inventory_mode = models.CharField(max_length=20, null=True, blank=True)
    user_id = models.UUIDField(null=True, blank=True)
    user_name = models.CharField(max_length=200, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'purchases_receipt'
        ordering = ['-receipt_date', '-created_at', 'id']
        indexes = [models.Index(fields=['company_id', 'purchase_id'], name='purch_receipt_company_purch')]


class ReceiptItemModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    receipt = models.ForeignKey(ReceiptModel, on_delete=models.CASCADE, related_name='items')
    position = models.PositiveIntegerField()
    # Línea de la compra y producto: solo UUID, sin FK.
    purchase_item_id = models.UUIDField()
    product_id = models.UUIDField()
    product_name = models.CharField(max_length=150)
    unit_abbreviation = models.CharField(max_length=10, blank=True, default='')
    quantity = models.DecimalField(max_digits=12, decimal_places=3)

    class Meta:
        db_table = 'purchases_receipt_item'
        ordering = ['position']
