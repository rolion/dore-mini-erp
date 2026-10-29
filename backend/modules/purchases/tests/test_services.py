from uuid import uuid4

from django.test import TestCase

from modules.purchases.infrastructure.django.repositories import DjangoSupplierRepository
from modules.purchases.domain.supplier import Supplier
from modules.purchases.services import SupplierForPurchase, get_supplier_for_purchase, list_active_suppliers


class SupplierFacadeTests(TestCase):
    def setUp(self):
        self.company_id = uuid4()
        self.other_company_id = uuid4()
        repo = DjangoSupplierRepository(self.company_id)
        self.active = repo.save(Supplier.create(name='Sur'))
        self.inactive = Supplier.create(name='Norte')
        self.inactive.deactivate()
        self.inactive = repo.save(self.inactive)
        self.foreign = DjangoSupplierRepository(self.other_company_id).save(Supplier.create(name='Ajeno'))

    def test_get_returns_dto_for_active_and_inactive(self):  # AC-08
        self.assertEqual(get_supplier_for_purchase(self.company_id, self.active.id),
                         SupplierForPurchase(id=self.active.id, name='Sur', active=True))
        self.assertEqual(get_supplier_for_purchase(self.company_id, self.inactive.id),
                         SupplierForPurchase(id=self.inactive.id, name='Norte', active=False))

    def test_get_returns_none_for_unknown_or_other_company(self):  # AC-08
        self.assertIsNone(get_supplier_for_purchase(self.company_id, uuid4()))
        self.assertIsNone(get_supplier_for_purchase(self.company_id, self.foreign.id))

    def test_list_active_only_from_the_company(self):  # AC-08
        self.assertEqual([s.name for s in list_active_suppliers(self.company_id)], ['Sur'])
        self.assertEqual([s.name for s in list_active_suppliers(self.other_company_id)], ['Ajeno'])

    def test_list_active_search_and_limit(self):  # AC-08
        DjangoSupplierRepository(self.company_id).save(Supplier.create(name='Surtidora', tax_id='NIT-9'))
        self.assertEqual([s.name for s in list_active_suppliers(self.company_id, search='nit-9')], ['Surtidora'])
        self.assertEqual(len(list_active_suppliers(self.company_id, limit=1)), 1)
