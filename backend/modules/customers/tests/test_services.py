from uuid import uuid4

from django.test import TestCase

from modules.customers.infrastructure.django.models import CustomerModel
from modules.customers.services import CustomerForSale, get_customer_for_sale, get_customer_names


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
