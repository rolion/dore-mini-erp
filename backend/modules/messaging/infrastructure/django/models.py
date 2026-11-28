import uuid

from django.db import models
from django.db.models import Q


class ConnectionModel(models.Model):
    """Número de WhatsApp de una empresa. Solo guarda NOMBRES de variables de entorno, nunca secretos."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(unique=True)
    waba_id = models.CharField(max_length=40)
    phone_number_id = models.CharField(max_length=40, unique=True)
    display_phone = models.CharField(max_length=20, blank=True)
    secret_ref = models.CharField(max_length=64)
    app_secret_ref = models.CharField(max_length=64)
    verify_token = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=10, default='pending')
    status_reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'messaging_connection'
        constraints = [models.CheckConstraint(condition=Q(status__in=['pending', 'active', 'error', 'disabled']),
                                              name='messaging_connection_status_valid')]


class TemplateModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    connection = models.ForeignKey(ConnectionModel, on_delete=models.CASCADE, related_name='templates')
    name = models.CharField(max_length=512)
    language = models.CharField(max_length=20)
    category = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20)
    components = models.JSONField(default=list)
    synced_at = models.DateTimeField()

    class Meta:
        db_table = 'messaging_template'
        ordering = ['name', 'language']
        constraints = [models.UniqueConstraint(fields=['connection', 'name', 'language'],
                                               name='messaging_template_unique')]


class ConversationModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    connection = models.ForeignKey(ConnectionModel, on_delete=models.CASCADE, related_name='conversations')
    phone = models.CharField(max_length=20)
    last_inbound_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'messaging_conversation'
        constraints = [models.UniqueConstraint(fields=['connection', 'phone'], name='messaging_conversation_unique')]


class MessageModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    connection = models.ForeignKey(ConnectionModel, on_delete=models.CASCADE, related_name='messages')
    conversation = models.ForeignKey(ConversationModel, on_delete=models.CASCADE, related_name='messages')
    provider_message_id = models.CharField(max_length=200, null=True, blank=True)
    direction = models.CharField(max_length=3)
    type = models.CharField(max_length=20)
    content = models.JSONField(default=dict)
    template = models.ForeignKey(TemplateModel, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=10, default='queued')
    pricing_category = models.CharField(max_length=40, blank=True)
    billable = models.BooleanField(null=True, blank=True)
    pricing_model = models.CharField(max_length=20, blank=True)
    cost = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    currency = models.CharField(max_length=3, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'messaging_message'
        ordering = ['created_at', 'id']
        indexes = [models.Index(fields=['status', 'next_attempt_at'], name='messaging_msg_queue_idx')]
        constraints = [
            models.UniqueConstraint(fields=['connection', 'provider_message_id'],
                                    condition=Q(provider_message_id__isnull=False),
                                    name='messaging_message_wamid_unique'),
            models.CheckConstraint(condition=Q(status__in=['queued', 'sent', 'delivered', 'read', 'failed']),
                                   name='messaging_message_status_valid'),
            models.CheckConstraint(condition=Q(direction__in=['in', 'out']), name='messaging_message_direction_valid'),
        ]


class WebhookEventModel(models.Model):
    """Cuerpo del webhook ya verificado (firma), a la espera de que el worker lo procese."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    connection = models.ForeignKey(ConnectionModel, on_delete=models.CASCADE, related_name='events')
    payload = models.JSONField()
    status = models.CharField(max_length=10, default='pending')
    failure_reason = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'messaging_webhook_event'
        ordering = ['created_at', 'id']
        indexes = [models.Index(fields=['status', 'created_at'], name='messaging_event_queue_idx')]
        constraints = [models.CheckConstraint(condition=Q(status__in=['pending', 'processing', 'done', 'failed']),
                                              name='messaging_event_status_valid')]
