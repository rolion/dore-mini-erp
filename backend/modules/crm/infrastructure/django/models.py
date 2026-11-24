import uuid

from django.db import models
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
