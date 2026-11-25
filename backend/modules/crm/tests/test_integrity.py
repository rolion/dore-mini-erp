"""Garantías de base de datos y carreras de prospectos/oportunidades (INV-04, INV-06, REV-02).

Cubre lo que las pruebas de API no ejecutan: la traducción del `IntegrityError` de la restricción única de pedido,
los `CheckConstraint` de `crm_opportunity` y la conversión simultánea del mismo prospecto.
"""
import threading
from datetime import datetime, timezone
from uuid import uuid4

from django.db import IntegrityError, connection, transaction
from django.test import TestCase, TransactionTestCase, override_settings

from modules.accounts.testing import make_company
from modules.crm.application.lead_services import LeadService
from modules.crm.domain.errors import CrmConflict
from modules.crm.infrastructure.adapters import CustomerGatewayAdapter
from modules.crm.infrastructure.django.models import BoardModel, LeadModel, OpportunityModel, StageModel
from modules.crm.infrastructure.django.repositories import DjangoLeadRepository, DjangoOpportunityRepository
from modules.customers.infrastructure.django.models import CustomerModel

NOW = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)


def make_opportunity(company, **overrides) -> OpportunityModel:
    name = f'T-{uuid4().hex[:6]}'
    board = overrides.pop('board', None) or BoardModel.objects.create(company_id=company.id, name=name)
    stage = overrides.pop('stage', None) or StageModel.objects.create(board=board, name='Nuevo', position=1)
    values = {'company_id': company.id, 'board': board, 'stage': stage, 'customer_id': uuid4(), 'owner_id': 1,
              'title': 'Pack', 'amount': 10, **overrides}
    return OpportunityModel.objects.create(**values)


class OrderUniquenessTests(TestCase):
    """INV-06: un pedido, una oportunidad, aunque la verificación de aplicación se salte (carrera)."""

    def setUp(self):
        self.company = make_company('CRM A')
        self.customer_id = uuid4()
        self.order_id = uuid4()

    def won(self, **extra):
        return make_opportunity(self.company, customer_id=self.customer_id, status='won', closed_at=NOW, **extra)

    def test_repository_translates_unique_violation_to_conflict_and_keeps_transaction_usable(self):
        first = self.won(order_id=self.order_id)
        rival = self.won()
        repository = DjangoOpportunityRepository(self.company.id)
        entity = repository.get(rival.id)
        self.assertTrue(entity.link_order(self.order_id, self.customer_id, order_cancelled=False))

        with self.assertRaises(CrmConflict) as raised:
            repository.save(entity)

        self.assertEqual(raised.exception.code, 'order_already_linked')
        # El savepoint deja la transacción utilizable y no toca ninguna de las dos filas.
        self.assertEqual(OpportunityModel.objects.get(pk=first.id).order_id, self.order_id)
        self.assertIsNone(OpportunityModel.objects.get(pk=rival.id).order_id)

    def test_database_rejects_duplicate_order_directly(self):
        self.won(order_id=self.order_id)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.won(order_id=self.order_id)

    def test_other_integrity_errors_are_not_masked(self):
        """Solo la restricción de pedido se traduce a 409: cualquier otra violación sube tal cual."""
        opportunity = make_opportunity(self.company)
        repository = DjangoOpportunityRepository(self.company.id)
        entity = repository.get(opportunity.id)
        entity.amount = -1  # el dominio lo impediría; aquí se fuerza para comprobar la restricción de BD
        with self.assertRaises(IntegrityError):
            repository.save(entity)


class CheckConstraintTests(TestCase):
    def setUp(self):
        self.company = make_company('CRM A')

    def assert_rejected(self, name, **overrides):
        with self.assertRaises(IntegrityError) as raised, transaction.atomic():
            make_opportunity(self.company, **overrides)
        self.assertIn(name, str(raised.exception))

    def test_contact_required(self):
        self.assert_rejected('crm_opportunity_contact_required', customer_id=None, lead=None)

    def test_amount_not_negative(self):
        self.assert_rejected('crm_opportunity_amount_gte_0', amount=-1)

    def test_status_must_be_known(self):
        # Un estado desconocido incumple a la vez la coherencia de cierre; PostgreSQL informa una de las dos.
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_opportunity(self.company, status='archived', closed_at=NOW)

    def test_closed_requires_closed_at_and_open_forbids_it(self):
        self.assert_rejected('crm_opportunity_closed_coherent', status='won')
        self.assert_rejected('crm_opportunity_closed_coherent', status='open', closed_at=NOW)
        self.assert_rejected('crm_opportunity_closed_coherent', status='open', order_id=uuid4())

    def test_lost_requires_reason(self):
        self.assert_rejected('crm_opportunity_lost_requires_reason', status='lost', closed_at=NOW, lost_reason='')


@override_settings(DEFAULT_PHONE_COUNTRY_CODE='591')
class ConcurrentConversionTests(TransactionTestCase):
    """INV-04: dos conversiones simultáneas del mismo prospecto crean un solo cliente."""

    def test_simultaneous_conversions_create_one_customer(self):
        company = make_company('CRM A')
        lead = LeadModel.objects.create(company_id=company.id, name='Ana', phone='76543210',
                                        normalized_phone='+59176543210')
        start = threading.Barrier(2)
        results, errors = [], []

        def worker():
            try:
                service = LeadService(DjangoLeadRepository(company.id), DjangoOpportunityRepository(company.id),
                                      CustomerGatewayAdapter(company.id))
                start.wait(timeout=10)
                with transaction.atomic():
                    results.append(service.convert(lead.id))
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
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].customer.id, results[1].customer.id)
        self.assertEqual(sorted(r.created for r in results), [False, True])
        self.assertEqual(CustomerModel.objects.filter(company_id=company.id).count(), 1)
        lead.refresh_from_db()
        self.assertEqual(lead.converted_customer_id, results[0].customer.id)
