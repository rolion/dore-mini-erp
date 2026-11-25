import uuid

from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower


class BoardModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=80)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'crm_board'
        ordering = ['created_at', 'id']
        constraints = [
            models.UniqueConstraint(Lower('name'), 'company_id', condition=models.Q(is_active=True),
                                    name='crm_board_active_name_unique'),
        ]


class StageModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    board = models.ForeignKey(BoardModel, on_delete=models.CASCADE, related_name='stages')
    name = models.CharField(max_length=80)
    position = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'crm_stage'
        ordering = ['position', 'id']
        constraints = [
            models.UniqueConstraint(Lower('name'), 'board', condition=models.Q(is_active=True),
                                    name='crm_stage_active_name_unique'),
        ]


class LeadModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30, blank=True, default='')
    # Calculado con la normalización de Clientes; sin unicidad (varias personas pueden compartir teléfono).
    normalized_phone = models.CharField(max_length=30, blank=True, default='')
    email = models.CharField(max_length=254, blank=True, default='')
    # Cliente de `customers` (solo UUID, sin FK entre contextos).
    converted_customer_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'crm_lead'
        ordering = ['-created_at', 'id']
        indexes = [models.Index(fields=['company_id', 'normalized_phone'], name='crm_lead_company_phone_idx')]


class OpportunityModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    board = models.ForeignKey(BoardModel, on_delete=models.PROTECT, related_name='opportunities')
    stage = models.ForeignKey(StageModel, on_delete=models.PROTECT, related_name='opportunities')
    lead = models.ForeignKey(LeadModel, on_delete=models.PROTECT, null=True, blank=True,
                             related_name='opportunities')
    # Referencias a otros contextos solo por id, sin FK: cliente y pedido (UUID) y responsable (usuario, entero).
    customer_id = models.UUIDField(null=True, blank=True, db_index=True)
    owner_id = models.BigIntegerField(db_index=True)
    order_id = models.UUIDField(null=True, blank=True)
    title = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='BOB')
    next_action_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, default='open')
    closed_at = models.DateTimeField(null=True, blank=True)
    lost_reason = models.CharField(max_length=500, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'crm_opportunity'
        ordering = ['created_at', 'id']
        indexes = [models.Index(fields=['board', 'stage', 'status'], name='crm_opp_board_stage_status_idx')]
        constraints = [
            models.CheckConstraint(condition=Q(lead__isnull=False) | Q(customer_id__isnull=False),
                                   name='crm_opportunity_contact_required'),
            models.CheckConstraint(condition=Q(amount__gte=0), name='crm_opportunity_amount_gte_0'),
            models.CheckConstraint(condition=Q(status__in=['open', 'won', 'lost']),
                                   name='crm_opportunity_status_valid'),
            models.CheckConstraint(
                condition=(Q(status='open', closed_at__isnull=True, order_id__isnull=True, lost_reason='')
                           | Q(status__in=['won', 'lost'], closed_at__isnull=False)),
                name='crm_opportunity_closed_coherent'),
            models.CheckConstraint(condition=~Q(status='lost') | ~Q(lost_reason=''),
                                   name='crm_opportunity_lost_requires_reason'),
            models.UniqueConstraint(fields=['order_id'], condition=Q(order_id__isnull=False),
                                    name='crm_opportunity_order_unique'),
        ]


class StageChangeModel(models.Model):
    """Historial de etapas: solo se agrega, nunca se edita."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    opportunity = models.ForeignKey(OpportunityModel, on_delete=models.CASCADE, related_name='stage_changes')
    from_stage = models.ForeignKey(StageModel, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    to_stage = models.ForeignKey(StageModel, on_delete=models.PROTECT, related_name='+')
    changed_by = models.BigIntegerField(null=True, blank=True)
    changed_at = models.DateTimeField()

    class Meta:
        db_table = 'crm_stage_change'
        ordering = ['changed_at', 'id']


class TaskModel(models.Model):
    """Tarea comercial; relacionada con exactamente un cliente (UUID de otro contexto) u oportunidad (FK local)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    customer_id = models.UUIDField(null=True, blank=True)
    opportunity = models.ForeignKey(OpportunityModel, on_delete=models.PROTECT, null=True, blank=True,
                                    related_name='tasks')
    owner_id = models.BigIntegerField()
    title = models.CharField(max_length=150)
    due_at = models.DateTimeField()
    status = models.CharField(max_length=10, default='pending')
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'crm_task'
        ordering = ['due_at', 'created_at', 'id']
        indexes = [
            models.Index(fields=['company_id', 'owner_id', 'status', 'due_at'], name='crm_task_owner_status_due_idx'),
            models.Index(fields=['company_id', 'customer_id'], name='crm_task_company_customer_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(Q(customer_id__isnull=False, opportunity__isnull=True)
                           | Q(customer_id__isnull=True, opportunity__isnull=False)),
                name='crm_task_exactly_one_related'),
            models.CheckConstraint(condition=Q(status__in=['pending', 'done', 'cancelled', 'archived']),
                                   name='crm_task_status_valid'),
            models.CheckConstraint(
                condition=(Q(status__in=['pending', 'cancelled'], completed_at__isnull=True)
                           | Q(status='done', completed_at__isnull=False) | Q(status='archived')),
                name='crm_task_completed_coherent'),
        ]


class ActivityModel(models.Model):
    """Actividad comercial: solo se agrega, nunca se edita ni se borra."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    actor_id = models.BigIntegerField()
    customer_id = models.UUIDField(null=True, blank=True)
    opportunity = models.ForeignKey(OpportunityModel, on_delete=models.PROTECT, null=True, blank=True,
                                    related_name='activities')
    task = models.ForeignKey(TaskModel, on_delete=models.PROTECT, null=True, blank=True, related_name='activities')
    channel = models.CharField(max_length=10)
    outcome = models.CharField(max_length=20, blank=True, default='')
    notes = models.CharField(max_length=2000, blank=True, default='')
    occurred_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'crm_activity'
        ordering = ['-occurred_at', '-created_at', 'id']
        indexes = [models.Index(fields=['company_id', 'customer_id', 'occurred_at'], name='crm_activity_customer_idx')]
        constraints = [
            models.CheckConstraint(
                condition=(Q(customer_id__isnull=False, opportunity__isnull=True)
                           | Q(customer_id__isnull=True, opportunity__isnull=False)),
                name='crm_activity_exactly_one_related'),
            models.CheckConstraint(condition=Q(channel__in=['call', 'whatsapp', 'email', 'visit', 'other']),
                                   name='crm_activity_channel_valid'),
        ]
