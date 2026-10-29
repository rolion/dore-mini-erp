from uuid import uuid4

from django.test import SimpleTestCase

from modules.purchases.application.commands import (
    ActivateSupplier,
    CreateSupplier,
    DeactivateSupplier,
    UpdateSupplier,
)
from modules.purchases.application.queries import GetSupplier, ListSuppliers
from modules.purchases.domain.exceptions import SupplierNotFound, SupplierValidationError


class InMemorySupplierRepository:
    def __init__(self):
        self.items = {}
        self.saves = 0

    def get(self, supplier_id):
        return self.items.get(supplier_id)

    def save(self, supplier):
        self.saves += 1
        self.items[supplier.id] = supplier
        return supplier

    def list(self, search=None, active=None):
        suppliers = sorted(self.items.values(), key=lambda s: (s.name, str(s.id)))
        if search:
            term = search.lower()
            suppliers = [s for s in suppliers if term in s.name.lower() or term in s.tax_id.lower()]
        if active is not None:
            suppliers = [s for s in suppliers if s.active is active]
        return suppliers


class SupplierUseCaseTests(SimpleTestCase):
    def setUp(self):
        self.repo = InMemorySupplierRepository()

    def create(self, name='Sur', **extra):
        return CreateSupplier(self.repo).execute(name=name, **extra)

    def update(self, supplier_id, **changes):
        return UpdateSupplier(self.repo).execute(supplier_id=supplier_id, **changes)

    def test_create_saves_active_supplier(self):  # AC-01
        supplier = self.create()
        self.assertTrue(supplier.active)
        self.assertIs(self.repo.get(supplier.id), supplier)

    def test_create_invalid_does_not_save(self):  # AC-02
        with self.assertRaises(SupplierValidationError):
            self.create(name='')
        self.assertEqual(self.repo.saves, 0)

    def test_update_changes_only_sent_fields(self):  # AC-03
        supplier = self.create(tax_id='1', phone='2', email='a@b.com', notes='n')
        updated = self.update(supplier.id, name='Norte', phone='')
        self.assertEqual((updated.name, updated.tax_id, updated.phone, updated.email, updated.notes),
                         ('Norte', '1', '', 'a@b.com', 'n'))

    def test_update_without_changes_does_not_save(self):  # AC-03
        supplier = self.create()
        saves = self.repo.saves
        self.update(supplier.id)
        self.assertEqual(self.repo.saves, saves)

    def test_update_invalid_changes_nothing(self):  # AC-02
        supplier = self.create(phone='1')
        saves = self.repo.saves
        with self.assertRaises(SupplierValidationError) as ctx:
            self.update(supplier.id, name='', email='mal', phone='2')
        self.assertEqual(set(ctx.exception.errors), {'name', 'email'})
        self.assertEqual(self.repo.saves, saves)

    def test_update_unknown_supplier(self):
        with self.assertRaises(SupplierNotFound):
            self.update(uuid4(), name='X')

    def test_deactivate_and_activate(self):  # AC-05
        supplier = self.create()
        self.assertFalse(DeactivateSupplier(self.repo).execute(supplier.id).active)
        self.assertEqual(list(ListSuppliers(self.repo).execute(active=True)), [])
        self.assertIs(GetSupplier(self.repo).execute(supplier.id), supplier)
        self.assertTrue(ActivateSupplier(self.repo).execute(supplier.id).active)

    def test_get_unknown_and_state_changes_on_unknown(self):
        for case in (GetSupplier(self.repo), ActivateSupplier(self.repo), DeactivateSupplier(self.repo)):
            with self.subTest(case=type(case).__name__), self.assertRaises(SupplierNotFound):
                case.execute(uuid4())

    def test_list_search_by_name_or_tax_id(self):  # AC-04
        self.create(name='Sur', tax_id='NIT-100')
        self.create(name='Norte', tax_id='NIT-200')
        names = lambda **kw: [s.name for s in ListSuppliers(self.repo).execute(**kw)]  # noqa: E731
        self.assertEqual(names(search='nor'), ['Norte'])
        self.assertEqual(names(search='100'), ['Sur'])
        self.assertEqual(names(), ['Norte', 'Sur'])
