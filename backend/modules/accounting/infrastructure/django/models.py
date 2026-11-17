import uuid

from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower


class AccountModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Empresa propietaria; solo UUID, sin FK (los módulos no acoplan modelos ni migraciones).
    company_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=80)
    currency = models.CharField(max_length=3)
    is_active = models.BooleanField(default=True)
    # Caja/Banco/Billetera; nulo en cuentas anteriores a su introducción.
    kind = models.CharField(max_length=10, null=True, blank=True)
    # Una de las seis clasificaciones contables (CONT-08); nula hasta que CONT-09 la haga obligatoria.
    account_class = models.CharField(max_length=10, null=True, blank=True)
    # Código del plan de cuentas (CONT-09); nulo en cuentas anteriores.
    code = models.CharField(max_length=20, null=True, blank=True)
    # Cuenta correctora (saldo normal contrario al de su clasificación).
    is_contra = models.BooleanField(default=False)
    # Monto a la fecha de corte; editable solo mientras la cuenta no tiene movimientos.
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounting_account'
        ordering = ['name', 'id']
        constraints = [
            models.UniqueConstraint(Lower('name'), 'company_id', name='accounting_account_name_ci_uniq'),
            models.UniqueConstraint(Lower('code'), 'company_id', condition=Q(code__isnull=False),
                                    name='accounting_account_code_ci_uniq'),
            models.CheckConstraint(condition=Q(opening_balance__gte=0), name='accounting_account_opening_gte_0'),
        ]


class AccountClassSettingModel(models.Model):
    """Estado por empresa de una clasificación contable fija; sin fila = habilitada."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    code = models.CharField(max_length=10)
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounting_account_class_setting'
        constraints = [
            models.UniqueConstraint(fields=['company_id', 'code'], name='accounting_account_class_company_uniq'),
        ]


class SettingsModel(models.Model):
    """Ajustes de Contabilidad de una empresa: fecha de corte (una por empresa)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(unique=True)
    cutoff_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'accounting_settings'


class CoveragePeriodModel(models.Model):
    """Tramo en que Contabilidad estuvo habilitada; los huecos entre tramos son periodos sin cobertura."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'accounting_coverage_period'
        ordering = ['started_at', 'id']
        constraints = [
            models.UniqueConstraint(fields=['company_id'], condition=Q(ended_at__isnull=True),
                                    name='accounting_coverage_one_open'),
        ]


class ClassificationModel(models.Model):
    """Clasificación de ingresos o egresos de una empresa (por qué se mueve el dinero)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=80)
    direction = models.CharField(max_length=10)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounting_classification'
        ordering = ['name', 'id']
        constraints = [
            models.UniqueConstraint(Lower('name'), 'company_id', 'direction',
                                    name='accounting_classification_name_dir_ci_uniq'),
        ]


class MethodMappingModel(models.Model):
    """Destino vigente de un método de pago por empresa (una fila por método)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    method = models.CharField(max_length=20)
    account = models.ForeignKey(AccountModel, null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounting_method_mapping'
        constraints = [
            models.UniqueConstraint(fields=['company_id', 'method'], name='accounting_mapping_method_uniq'),
        ]


class EntryModel(models.Model):
    """Entrada del libro: movimiento de dinero de un origen (ingreso o egreso). Solo se inserta; nunca se actualiza ni se borra."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    # Cuenta usada al cobrar; las cuentas no se eliminan, por eso PROTECT.
    account = models.ForeignKey(AccountModel, on_delete=models.PROTECT, related_name='+')
    currency = models.CharField(max_length=3)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField()
    payment_method = models.CharField(max_length=20)
    # Pago de origen por UUID (sin FK entre módulos) y datos de trazabilidad en texto.
    origin_kind = models.CharField(max_length=20)
    origin_id = models.UUIDField()
    origin_document_ref = models.CharField(max_length=60, blank=True, default='')
    receipt_number = models.CharField(max_length=20, blank=True, default='')
    recorded_by = models.BigIntegerField(null=True, blank=True)
    recorded_by_name = models.CharField(max_length=150, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    # Regularización de pagos históricos (PB-ACC-004): fecha y ejecutor aparte del autor del cobro original.
    regularized_at = models.DateTimeField(null=True, blank=True)
    regularized_by_name = models.CharField(max_length=150, blank=True, default='')
    # INCOME (cobro) o EXPENSE (gasto, pago de compra); la deriva el origen.
    direction = models.CharField(max_length=10, default='INCOME')
    # RECORD (original) o REVERSAL (movimiento opuesto vinculado al original).
    operation = models.CharField(max_length=10, default='RECORD')
    # Clasificación (por qué se mueve el dinero); obligatoria en egresos. Solo UUID: es un dato del mismo módulo.
    classification_id = models.UUIDField(null=True, blank=True)
    reverses = models.OneToOneField('self', null=True, blank=True, on_delete=models.PROTECT,
                                    related_name='reversed_by_entry')

    class Meta:
        db_table = 'accounting_entry'
        ordering = ['-payment_date', '-created_at', 'id']
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name='accounting_entry_amount_gt_0'),
            models.UniqueConstraint(fields=['company_id', 'origin_kind', 'origin_id', 'operation'],
                                    name='accounting_entry_origin_op_uniq'),
            models.CheckConstraint(
                condition=(Q(operation='RECORD', reverses__isnull=True) | Q(operation='REVERSAL', reverses__isnull=False)),
                name='accounting_entry_reversal_link'),
        ]
        indexes = [
            models.Index(fields=['company_id', 'payment_date'], name='accounting_entry_date'),
            models.Index(fields=['company_id', 'account'], name='accounting_entry_account'),
        ]


class FiscalPeriodModel(models.Model):
    """Período fiscal de una empresa: rango inclusivo de fechas con estado abierto/cerrado."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=80)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=6, default='OPEN')
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by_name = models.CharField(max_length=150, blank=True, default='')
    reopened_at = models.DateTimeField(null=True, blank=True)
    reopened_by_name = models.CharField(max_length=150, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounting_fiscal_period'
        ordering = ['-start_date', 'id']
        constraints = [
            models.CheckConstraint(condition=Q(start_date__lte=models.F('end_date')),
                                   name='accounting_fiscal_period_dates'),
            models.CheckConstraint(condition=Q(status__in=['OPEN', 'CLOSED']), name='accounting_fiscal_period_status'),
            models.UniqueConstraint(Lower('name'), 'company_id', name='accounting_fiscal_period_name_ci_uniq'),
        ]
        indexes = [models.Index(fields=['company_id', 'start_date'], name='accounting_fperiod_start')]


class JournalEntryModel(models.Model):
    """Cabecera de un asiento de partida doble (CONT-02). Solo se inserta; nunca se actualiza ni se borra."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    accounting_date = models.DateField()
    description = models.CharField(max_length=200)
    # MANUAL (sin origen) o AUTOMATIC (con origen); una reversión conserva el de su original.
    source = models.CharField(max_length=10)
    # Referencia única de evento de un asiento automático: tipo + id en el módulo de origen (sin FK entre módulos).
    origin_kind = models.CharField(max_length=30, null=True, blank=True)
    origin_id = models.UUIDField(null=True, blank=True)
    currency = models.CharField(max_length=3)
    # Suma del Debe (= suma del Haber).
    total = models.DecimalField(max_digits=12, decimal_places=2)
    period = models.ForeignKey(FiscalPeriodModel, on_delete=models.PROTECT, related_name='+')
    created_by = models.BigIntegerField(null=True, blank=True)
    created_by_name = models.CharField(max_length=150, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    # Solo en reversiones: el asiento original (a lo sumo una reversión por original) y su motivo.
    reverses = models.OneToOneField('self', null=True, blank=True, on_delete=models.PROTECT,
                                    related_name='reversed_by_entry')
    reversal_reason = models.CharField(max_length=200, blank=True, default='')

    class Meta:
        db_table = 'accounting_journal_entry'
        ordering = ['-accounting_date', '-created_at', '-id']
        constraints = [
            models.CheckConstraint(condition=Q(total__gt=0), name='accounting_journal_total_gt_0'),
            models.CheckConstraint(condition=Q(source__in=['MANUAL', 'AUTOMATIC']), name='accounting_journal_source'),
            models.CheckConstraint(
                condition=(Q(origin_kind__isnull=True, origin_id__isnull=True)
                           | Q(origin_kind__isnull=False, origin_id__isnull=False)),
                name='accounting_journal_origin_pair'),
            models.CheckConstraint(
                condition=(Q(reverses__isnull=True, reversal_reason='')
                           | (Q(reverses__isnull=False, origin_id__isnull=True) & ~Q(reversal_reason=''))),
                name='accounting_journal_reversal_shape'),
            models.UniqueConstraint(fields=['company_id', 'origin_kind', 'origin_id'],
                                    condition=Q(origin_id__isnull=False), name='accounting_journal_origin_uniq'),
        ]
        indexes = [
            models.Index(fields=['company_id', 'accounting_date'], name='accounting_journal_date'),
            models.Index(fields=['company_id', 'period'], name='accounting_journal_period'),
        ]


class JournalLineModel(models.Model):
    """Línea de un asiento: una cuenta con Debe o Haber. Solo se inserta."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entry = models.ForeignKey(JournalEntryModel, on_delete=models.PROTECT, related_name='lines')
    company_id = models.UUIDField()
    position = models.PositiveSmallIntegerField()
    account = models.ForeignKey(AccountModel, on_delete=models.PROTECT, related_name='+')
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    memo = models.CharField(max_length=200, blank=True, default='')

    class Meta:
        db_table = 'accounting_journal_line'
        ordering = ['position']
        constraints = [
            models.CheckConstraint(
                condition=(Q(debit__gt=0, credit=0) | Q(debit=0, credit__gt=0)), name='accounting_journal_line_side'),
            models.UniqueConstraint(fields=['entry', 'position'], name='accounting_journal_line_position_uniq'),
        ]
        indexes = [models.Index(fields=['company_id', 'account'], name='accounting_jline_account')]


class PostingAccountModel(models.Model):
    """Cuenta elegida por la empresa para un rol (`ROLE`) o una categoría de gasto (`CATEGORY`) de los asientos
    automáticos (CONT-12). El método de pago → cuenta sigue en `MethodMappingModel`. Sin fila = sin configurar."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    scope = models.CharField(max_length=10)
    # Código del rol del catálogo, o id de la clasificación de gasto (texto).
    key = models.CharField(max_length=40)
    account = models.ForeignKey(AccountModel, on_delete=models.PROTECT, related_name='+')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounting_posting_account'
        constraints = [
            models.UniqueConstraint(fields=['company_id', 'scope', 'key'], name='accounting_posting_account_uniq'),
            models.CheckConstraint(condition=Q(scope__in=['ROLE', 'CATEGORY']), name='accounting_posting_scope'),
        ]
