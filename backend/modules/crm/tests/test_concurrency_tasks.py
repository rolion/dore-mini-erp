"""Transiciones concurrentes de tareas (INV-02, doble clic en «Completar»): la fila se bloquea y solo una gana."""
import threading
from datetime import datetime, timedelta, timezone

from django.db import connection, transaction
from django.test import TransactionTestCase

from modules.accounts.testing import make_company
from modules.crm.application.related import RelatedEntities
from modules.crm.application.task_services import TaskService
from modules.crm.domain.errors import CrmConflict
from modules.crm.infrastructure.adapters import CustomerGatewayAdapter, UserDirectoryAdapter
from modules.crm.infrastructure.django.models import ActivityModel, TaskModel
from modules.crm.infrastructure.django.repositories import (
    DjangoActivityRepository,
    DjangoOpportunityRepository,
    DjangoTaskRepository,
)
from modules.customers.infrastructure.django.models import CustomerModel

NOW = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)


class ConcurrentTaskTests(TransactionTestCase):
    def test_simultaneous_completions_apply_once_and_record_one_activity(self):
        company = make_company('CRM A')
        customer = CustomerModel.objects.create(company_id=company.id, name='Ana', phone='76543210')
        service = self.service(company.id)
        task = service.create(actor_id=1, title='Llamar', due_at=NOW + timedelta(days=1), customer_id=customer.id,
                              owner_id=None)
        start = threading.Barrier(2)
        outcomes, errors = [], []

        def worker():
            try:
                worker_service = self.service(company.id)
                start.wait(timeout=10)
                with transaction.atomic():
                    worker_service.complete(task.id, actor_id=1, activity={'channel': 'call', 'notes': 'ok'})
                outcomes.append('done')
            except CrmConflict:
                outcomes.append('conflict')
            except Exception as exc:  # noqa: BLE001 - se reporta en el hilo principal
                errors.append(exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        self.assertEqual(errors, [])
        self.assertEqual(sorted(outcomes), ['conflict', 'done'])
        self.assertEqual(TaskModel.objects.get(pk=task.id).status, 'done')
        self.assertEqual(ActivityModel.objects.filter(task_id=task.id).count(), 1)

    @staticmethod
    def service(company_id) -> TaskService:
        return TaskService(
            tasks=DjangoTaskRepository(company_id), activities=DjangoActivityRepository(company_id),
            related=RelatedEntities(customers=CustomerGatewayAdapter(company_id),
                                    opportunities=DjangoOpportunityRepository(company_id)),
            users=UserDirectoryAdapter(company_id), clock=lambda: NOW)
