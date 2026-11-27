from uuid import uuid4

from django.test import TestCase, override_settings

from modules.customers.infrastructure.django.models import CustomerModel
from modules.customers.services import (
    CustomerContactForCrm,
    CustomerForSale,
    CustomerRejected,
    create_customer_for_crm,
    find_active_customers_by_phone,
    get_customer_for_crm,
    get_customer_for_sale,
    get_customer_names,
    get_customers_for_crm,
    normalize_phone_for_crm,
)


COMPANY_ID = uuid4()


class GetCustomerForSaleTests(TestCase):
    def test_returns_name_and_state(self):  # AC-21
        customer = CustomerModel.objects.create(company_id=COMPANY_ID, name='Ana')
        self.assertEqual(get_customer_for_sale(COMPANY_ID, customer.id), CustomerForSale(id=customer.id, name='Ana', active=True))

    def test_inactive_customers_are_returned_with_their_state(self):  # AC-21, EDGE-08
        customer = CustomerModel.objects.create(company_id=COMPANY_ID, name='Luis', active=False)
        self.assertFalse(get_customer_for_sale(COMPANY_ID, customer.id).active)

    def test_unknown_customer_returns_none(self):  # AC-21
        self.assertIsNone(get_customer_for_sale(COMPANY_ID, uuid4()))


class GetCustomerNamesTests(TestCase):
    def test_returns_names_by_id_in_one_query(self):  # AC-21
        ana = CustomerModel.objects.create(company_id=COMPANY_ID, name='Ana')
        luis = CustomerModel.objects.create(company_id=COMPANY_ID, name='Luis', active=False)
        with self.assertNumQueries(1):
            names = get_customer_names(COMPANY_ID, [ana.id, luis.id, uuid4()])
        self.assertEqual(names, {ana.id: 'Ana', luis.id: 'Luis'})

    def test_empty_input_does_not_query(self):  # AC-21
        with self.assertNumQueries(0):
            self.assertEqual(get_customer_names(COMPANY_ID, []), {})

    def test_names_of_another_company_are_not_returned(self):  # AC-06 / AC-08
        mine = CustomerModel.objects.create(company_id=COMPANY_ID, name='Ana')
        foreign = CustomerModel.objects.create(company_id=uuid4(), name='Ajeno')
        self.assertEqual(get_customer_names(COMPANY_ID, [mine.id, foreign.id]), {mine.id: 'Ana'})
        self.assertIsNone(get_customer_for_sale(COMPANY_ID, foreign.id))


@override_settings(DEFAULT_PHONE_COUNTRY_CODE='591')
class CrmProspectFacadeTests(TestCase):  # TASK-crm-prospectos-oportunidades
    def test_normalize_phone_matches_customers(self):
        self.assertEqual(normalize_phone_for_crm(' 765-43210 '), '+59176543210')
        self.assertEqual(normalize_phone_for_crm('ext 12'), 'ext 12')
        self.assertEqual(normalize_phone_for_crm('   '), '')

    def test_find_active_by_phone_only_in_company(self):
        ana = CustomerModel.objects.create(company_id=COMPANY_ID, name='Ana', phone='+59176543210')
        CustomerModel.objects.create(company_id=COMPANY_ID, name='Inactiva', phone='+59176543210', active=False)
        CustomerModel.objects.create(company_id=uuid4(), name='Ajena', phone='+59176543210')
        self.assertEqual(find_active_customers_by_phone(COMPANY_ID, '+59176543210'),
                         [CustomerContactForCrm(ana.id, 'Ana', '+59176543210', True)])
        self.assertEqual(find_active_customers_by_phone(COMPANY_ID, ''), [])

    def test_get_and_get_many_are_company_scoped(self):
        ana = CustomerModel.objects.create(company_id=COMPANY_ID, name='Ana', active=False)
        foreign = CustomerModel.objects.create(company_id=uuid4(), name='Ajena')
        self.assertEqual(get_customer_for_crm(COMPANY_ID, ana.id), CustomerContactForCrm(ana.id, 'Ana', '', False))
        self.assertIsNone(get_customer_for_crm(COMPANY_ID, foreign.id))
        with self.assertNumQueries(1):
            self.assertEqual(set(get_customers_for_crm(COMPANY_ID, [ana.id, foreign.id, uuid4()])), {ana.id})
        with self.assertNumQueries(0):
            self.assertEqual(get_customers_for_crm(COMPANY_ID, []), {})

    def test_create_uses_customer_rules_without_duplicate_prompt(self):
        CustomerModel.objects.create(company_id=COMPANY_ID, name='Ana', phone='+59176543210')
        created = create_customer_for_crm(COMPANY_ID, 'Ana Nueva', '76543210', 'ana@example.com')
        stored = CustomerModel.objects.get(pk=created.id)
        self.assertEqual((stored.company_id, stored.name, stored.phone, stored.email, stored.active),
                         (COMPANY_ID, 'Ana Nueva', '+59176543210', 'ana@example.com', True))
        with self.assertRaises(CustomerRejected) as ctx:
            create_customer_for_crm(COMPANY_ID, '  ', '', 'mal')
        self.assertEqual(set(ctx.exception.errors), {'name', 'email'})
