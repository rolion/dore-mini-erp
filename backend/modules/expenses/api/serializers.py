from rest_framework import serializers

# --- Entrada: solo forma y tipos. Las reglas (obligatoriedad, rangos, estados) las aplica el dominio, que junta ---
# --- los errores de todos los campos. Los campos de estado y auditoría no se aceptan y se ignoran. --------------


class ExpenseInputSerializer(serializers.Serializer):
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    # Texto (o número JSON): el dominio valida formato, rango y decimales y junta los errores de todos los campos.
    amount = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    category_id = serializers.UUIDField(required=False, allow_null=True)
    expense_date = serializers.DateField(required=False, allow_null=True)
    payment_method = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    supplier_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class ExpenseCreateSerializer(ExpenseInputSerializer):
    """Alta: además de los datos del gasto, las cuentas elegidas (opcionales) y la clave de idempotencia."""

    expense_account_id = serializers.UUIDField(required=False, allow_null=True)
    payment_account_id = serializers.UUIDField(required=False, allow_null=True)
    idempotency_key = serializers.UUIDField(required=False, allow_null=True)


class PostingOptionsQuerySerializer(serializers.Serializer):
    expense_date = serializers.DateField()
    category_id = serializers.UUIDField(required=False, allow_null=True)
    payment_method = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class CategoryInputSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class CategoryClassificationInputSerializer(serializers.Serializer):
    classification_id = serializers.UUIDField(allow_null=True)


# --- Salida ---------------------------------------------------------------------------------------------------


def _classification(classification_id, classifications):
    """`{id, name, active}` de la clasificación (el contexto trae las de la página), o `None` si no hay."""
    if classification_id is None:
        return None
    info = classifications.get(classification_id)
    if info is None:
        return {'id': classification_id, 'name': '', 'active': False}
    return {'id': info.id, 'name': info.name, 'active': info.active}


def account_data(info) -> dict:
    return {'id': info.id, 'code': info.code, 'name': info.name, 'active': info.is_active}


def _account(account_id, accounts):
    """`{id, code, name, active}` de la cuenta contable (el contexto trae las de la página), o `None`."""
    if account_id is None:
        return None
    info = accounts.get(account_id)
    return account_data(info) if info else {'id': account_id, 'code': None, 'name': '', 'active': False}


class CategorySerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    active = serializers.BooleanField(read_only=True)
    classification = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def get_classification(self, obj):
        return _classification(obj.classification_id, self.context.get('classifications', {}))


class _CategoryRefSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    active = serializers.BooleanField(read_only=True)


class ExpenseSummarySerializer(serializers.Serializer):
    """Forma de la lista; la categoría llega por contexto (`categories`, una consulta por lote)."""

    id = serializers.UUIDField(read_only=True)
    description = serializers.CharField(read_only=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    expense_date = serializers.DateField(read_only=True)
    category = serializers.SerializerMethodField()
    payment_method = serializers.SerializerMethodField()
    supplier_name = serializers.CharField(read_only=True)
    status = serializers.SerializerMethodField()
    voided_at = serializers.DateTimeField(read_only=True)
    classification = serializers.SerializerMethodField()
    posted = serializers.SerializerMethodField()
    expense_account = serializers.SerializerMethodField()
    payment_account = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def get_classification(self, obj):
        return _classification(obj.classification_id, self.context.get('classifications', {}))

    def get_posted(self, obj) -> bool:
        return obj.is_posted

    def get_expense_account(self, obj):
        return _account(obj.expense_account_id, self.context.get('accounts', {}))

    def get_payment_account(self, obj):
        return _account(obj.payment_account_id, self.context.get('accounts', {}))

    def get_category(self, obj):
        category = self.context.get('categories', {}).get(obj.category_id)
        if category is None:
            return {'id': obj.category_id, 'name': '', 'active': False}
        return _CategoryRefSerializer(category).data

    def get_payment_method(self, obj) -> str:
        return obj.payment_method.value

    def get_status(self, obj) -> str:
        return obj.status.value


class ExpenseSerializer(ExpenseSummarySerializer):
    notes = serializers.CharField(read_only=True)
    journal_entry_id = serializers.SerializerMethodField()

    def get_journal_entry_id(self, obj):
        return self.context.get('journal_entry_id')
