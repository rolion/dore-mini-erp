from uuid import uuid4

from django.test import SimpleTestCase

from modules.customers.application.commands import (
    ActivateCustomer,
    CreateCustomer,
    DeactivateCustomer,
    UpdateCustomer,
)
from modules.customers.application.exceptions import DuplicateCustomerPhone
from modules.customers.application.queries import GetCustomer, ListCustomers
from modules.customers.domain.exceptions import CustomerNotFound, CustomerValidationError

CC = '591'


class InMemoryCustomerRepository:
    def __init__(self):
        self.items = {}
        self.saves = 0

    def get(self, customer_id):
        return self.items.get(customer_id)

    def save(self, customer):
        self.saves += 1
        self.items[customer.id] = customer
        return customer

    def list(self, search=None, active=None):
        customers = sorted(self.items.values(), key=lambda c: (c.name, str(c.id)))
        if search:
            customers = [c for c in customers if search.lower() in c.name.lower()]
        if active is not None:
            customers = [c for c in customers if c.active is active]
        return customers

    def find_by_phone(self, phone, exclude_id=None, limit=10):
        found = [c for c in self.items.values() if c.phone == phone and c.id != exclude_id]
        return sorted(found, key=lambda c: (c.name, str(c.id)))[:limit]


class CustomerUseCaseTests(SimpleTestCase):
    def setUp(self):
        self.repo = InMemoryCustomerRepository()

    def create(self, name='Ana', **extra):
        return CreateCustomer(self.repo, CC).execute(name=name, **extra)

    def update(self, customer_id, **changes):
        return UpdateCustomer(self.repo, CC).execute(customer_id=customer_id, **changes)

    def test_create_with_name_only_saves_active_customer(self):  # AC-01
        customer = self.create()
        self.assertTrue(customer.active)
        self.assertIs(self.repo.get(customer.id), customer)

    def test_create_invalid_does_not_save(self):  # AC-02
        with self.assertRaises(CustomerValidationError):
            self.create(name=' ')
        self.assertEqual(self.repo.saves, 0)

    def test_create_without_phone_does_not_check_duplicates(self):  # AC-04
        self.create(name='A')
        self.create(name='B')
        self.assertEqual(len(self.repo.items), 2)

    def test_duplicate_phone_raises_with_matches_and_does_not_save(self):  # AC-04, EDGE-02
        first = self.create(name='Ana', phone='76543210')
        with self.assertRaises(DuplicateCustomerPhone) as ctx:
            self.create(name='Otra', phone='+591 7654-3210')
        self.assertEqual(ctx.exception.matches, [first])
        self.assertEqual(self.repo.saves, 1)

    def test_duplicate_confirmed_creates_second_customer(self):  # AC-04, INV-06
        self.create(name='Ana', phone='76543210')
        second = self.create(name='Otra', phone='76543210', confirm_duplicate=True)
        self.assertEqual(len(self.repo.items), 2)
        self.assertIn(second.id, self.repo.items)

    def test_duplicate_includes_inactive_customers(self):  # EDGE-03
        first = self.create(name='Ana', phone='76543210')
        DeactivateCustomer(self.repo).execute(first.id)
        with self.assertRaises(DuplicateCustomerPhone) as ctx:
            self.create(name='Otra', phone='76543210')
        self.assertFalse(ctx.exception.matches[0].active)

    def test_duplicate_of_not_normalizable_phone_uses_trimmed_text(self):  # EDGE-04
        self.create(name='Ana', phone='abc')
        with self.assertRaises(DuplicateCustomerPhone):
            self.create(name='Otra', phone=' abc ')

    def test_duplicate_matches_are_limited_to_ten(self):  # EDGE-05
        for i in range(12):
            self.create(name=f'C{i:02d}', phone='76543210', confirm_duplicate=True)
        with self.assertRaises(DuplicateCustomerPhone) as ctx:
            self.create(name='Nuevo', phone='76543210')
        self.assertEqual(len(ctx.exception.matches), 10)

    def test_confirm_without_duplicate_creates_normally(self):  # EDGE-09
        customer = self.create(phone='76543210', confirm_duplicate=True)
        self.assertEqual(customer.phone, '+59176543210')

    def test_update_changes_only_given_fields(self):  # AC-05
        customer = self.create(name='Ana', phone='76543210', email='a@x.com', notes='n')
        updated = self.update(customer.id, name='Beatriz')
        self.assertEqual((updated.name, updated.phone, updated.email, updated.notes),
                         ('Beatriz', '+59176543210', 'a@x.com', 'n'))
        self.assertEqual(updated.id, customer.id)

    def test_update_phone_normalizes_and_can_clear(self):  # AC-03, EDGE-07
        customer = self.create(phone='76543210', email='a@x.com')
        self.assertEqual(self.update(customer.id, phone='71111111').phone, '+59171111111')
        cleared = self.update(customer.id, phone='')
        self.assertEqual((cleared.phone, cleared.email), ('', 'a@x.com'))

    def test_update_does_not_check_duplicates_nor_change_state(self):  # AC-05, INV-04
        self.create(name='Ana', phone='76543210')
        other = self.create(name='Otra', phone='71111111')
        DeactivateCustomer(self.repo).execute(other.id)
        updated = self.update(other.id, phone='76543210')
        self.assertEqual(updated.phone, '+59176543210')
        self.assertFalse(updated.active)

    def test_update_with_invalid_data_reports_all_errors_and_does_not_save(self):  # AC-02
        customer = self.create()
        saves = self.repo.saves
        with self.assertRaises(CustomerValidationError) as ctx:
            self.update(customer.id, name='', email='mal')
        self.assertEqual(set(ctx.exception.errors), {'name', 'email'})
        self.assertEqual(self.repo.saves, saves)

    def test_update_without_changes_does_not_save(self):  # AC-05
        customer = self.create()
        saves = self.repo.saves
        self.update(customer.id)
        self.assertEqual(self.repo.saves, saves)

    def test_update_unknown_raises_not_found(self):  # AC-08
        with self.assertRaises(CustomerNotFound):
            self.update(uuid4(), name='x')

    def test_activate_and_deactivate(self):  # AC-07
        customer = self.create()
        self.assertFalse(DeactivateCustomer(self.repo).execute(customer.id).active)
        self.assertTrue(ActivateCustomer(self.repo).execute(customer.id).active)
        for use_case in (ActivateCustomer, DeactivateCustomer):
            with self.assertRaises(CustomerNotFound):
                use_case(self.repo).execute(uuid4())

    def test_get_and_list(self):  # AC-06, AC-08
        a = self.create(name='Ana')
        b = self.create(name='Beto')
        DeactivateCustomer(self.repo).execute(b.id)
        self.assertIs(GetCustomer(self.repo).execute(a.id), a)
        with self.assertRaises(CustomerNotFound):
            GetCustomer(self.repo).execute(uuid4())
        self.assertEqual([c.name for c in ListCustomers(self.repo).execute()], ['Ana', 'Beto'])
        self.assertEqual([c.name for c in ListCustomers(self.repo).execute(active=True)], ['Ana'])
        self.assertEqual([c.name for c in ListCustomers(self.repo).execute(search='bet')], ['Beto'])
