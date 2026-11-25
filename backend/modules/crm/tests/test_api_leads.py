"""API de prospectos y conversión en cliente (AC-01, AC-05, AC-09), con dos empresas."""
from decimal import Decimal
from uuid import uuid4

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.crm.infrastructure.django.models import BoardModel, LeadModel, OpportunityModel, StageModel
from modules.customers.infrastructure.django.models import CustomerModel

URL = '/api/crm/leads/'


@override_settings(DEFAULT_PHONE_COUNTRY_CODE='591')
class LeadApiBase(APITestCase):
    def setUp(self):
        self.company = make_company('CRM A')
        self.user = make_admin(self.company, username='crm-admin')
        authenticate(self.client, self.user)

    def create(self, name='Ana', phone='', email='', expected=201):
        response = self.client.post(URL, {'name': name, 'phone': phone, 'email': email}, format='json')
        self.assertEqual(response.status_code, expected, response.content)
        return response.json()

    def customer(self, name, phone='', active=True, company=None):
        return CustomerModel.objects.create(company_id=(company or self.company).id, name=name, phone=phone,
                                            active=active)

    def convert(self, lead_id, expected=200, **data):
        response = self.client.post(f'{URL}{lead_id}/convert/', data, format='json')
        self.assertEqual(response.status_code, expected, response.content)
        return response.json()


class LeadCrudTests(LeadApiBase):
    def test_create_normalizes_phone_and_scopes_to_company(self):  # AC-01
        body = self.client.post(URL, {'name': '  Ana  ', 'phone': '765 43210', 'email': 'ana@example.com',
                                      'company_id': str(uuid4())}, format='json').json()
        self.assertEqual(set(body), {'id', 'name', 'phone', 'normalized_phone', 'email', 'converted_customer_id',
                                     'created_at'})
        self.assertEqual((body['name'], body['phone'], body['normalized_phone'], body['converted_customer_id']),
                         ('Ana', '765 43210', '+59176543210', None))
        self.assertEqual(LeadModel.objects.get(pk=body['id']).company_id, self.company.id)

    def test_name_required_and_email_validated(self):  # AC-01
        for data in ({'name': '   '}, {'name': 'x' * 151}, {'name': 'Ana', 'email': 'mal'}, {}):
            response = self.client.post(URL, data, format='json')
            self.assertEqual(response.status_code, 400, data)

    def test_without_phone_and_unnormalizable_phone(self):  # edge cases
        self.assertEqual(self.create('Sin teléfono')['normalized_phone'], '')
        self.assertEqual(self.create('Raro', phone=' ext 12 ')['normalized_phone'], 'ext 12')

    def test_edit_and_detail(self):  # AC-01
        lead = self.create('Ana', phone='76543210')
        url = f"{URL}{lead['id']}/"
        body = self.client.patch(url, {'name': 'Ana María', 'phone': '71234567'}, format='json').json()
        self.assertEqual((body['name'], body['normalized_phone'], body['email']), ('Ana María', '+59171234567', ''))
        self.assertEqual(self.client.get(url).json()['name'], 'Ana María')
        self.assertEqual(self.client.patch(url, {'name': ''}, format='json').status_code, 400)
        cleared = self.client.patch(url, {'phone': ''}, format='json').json()
        self.assertEqual((cleared['phone'], cleared['normalized_phone']), ('', ''))

    def test_list_search_filter_and_pagination(self):  # AC-01
        ana = self.create('Ana', phone='76543210')
        self.create('Beto', email='beto@example.com')
        self.create('Carla')
        LeadModel.objects.filter(pk=ana['id']).update(converted_customer_id=uuid4())

        def names(**params):
            return sorted(r['name'] for r in self.client.get(URL, params).json()['results'])

        self.assertEqual(names(), ['Ana', 'Beto', 'Carla'])
        self.assertEqual(names(search='ana'), ['Ana'])
        self.assertEqual(names(search='7654'), ['Ana'])
        self.assertEqual(names(search='beto@'), ['Beto'])
        self.assertEqual(names(converted='true'), ['Ana'])
        self.assertEqual(names(converted='false'), ['Beto', 'Carla'])
        self.assertEqual(self.client.get(URL, {'converted': 'maybe'}).status_code, 400)
        page = self.client.get(URL, {'page_size': 2}).json()
        self.assertEqual((page['count'], len(page['results'])), (3, 2))


class LeadConvertTests(LeadApiBase):
    def test_creates_customer_when_no_match_and_is_idempotent(self):  # AC-05, INV-04
        lead = self.create('Ana', phone='76543210', email='ana@example.com')
        first = self.convert(lead['id'])
        self.assertTrue(first['created'])
        customer = CustomerModel.objects.get(pk=first['customer']['id'])
        self.assertEqual((customer.company_id, customer.name, customer.phone, customer.email),
                         (self.company.id, 'Ana', '+59176543210', 'ana@example.com'))
        self.assertEqual(first['lead']['converted_customer_id'], str(customer.id))
        again = self.convert(lead['id'])  # doble clic / reintento
        self.assertEqual((again['created'], again['customer']['id']), (False, str(customer.id)))
        self.assertEqual(CustomerModel.objects.filter(company_id=self.company.id).count(), 1)
        other = self.customer('Otro')
        self.assertEqual(self.convert(lead['id'], customer_id=str(other.id))['customer']['id'], str(customer.id))

    def test_links_single_active_match_by_phone(self):  # AC-05, INV-05
        existing = self.customer('Ana Cliente', phone='+59176543210')
        self.customer('Inactiva', phone='+59176543210', active=False)
        self.customer('Ajena', phone='+59176543210', company=make_company('CRM B'))
        lead = self.create('Ana', phone='7654-3210')
        body = self.convert(lead['id'])
        self.assertEqual((body['created'], body['customer']['id']), (False, str(existing.id)))
        self.assertEqual(CustomerModel.objects.filter(company_id=self.company.id).count(), 2)

    def test_multiple_matches_require_choice(self):  # AC-05
        a = self.customer('Ana A', phone='+59176543210')
        b = self.customer('Ana B', phone='+59176543210')
        lead = self.create('Ana', phone='76543210')
        conflict = self.convert(lead['id'], expected=409)
        self.assertEqual(conflict['code'], 'multiple_customer_matches')
        self.assertEqual({c['id'] for c in conflict['candidates']}, {str(a.id), str(b.id)})
        self.assertIsNone(LeadModel.objects.get(pk=lead['id']).converted_customer_id)
        chosen = self.convert(lead['id'], customer_id=str(b.id))
        self.assertEqual((chosen['created'], chosen['customer']['id']), (False, str(b.id)))

    def test_lead_without_phone_creates_customer_without_phone(self):  # edge case
        body = self.convert(self.create('Sin teléfono')['id'])
        self.assertTrue(body['created'])
        self.assertEqual(CustomerModel.objects.get(pk=body['customer']['id']).phone, '')

    def test_chosen_customer_must_be_active_and_of_company(self):  # AC-05, INV-01
        lead = self.create('Ana')
        foreign = self.customer('Ajeno', company=make_company('CRM B'))
        self.convert(lead['id'], expected=404, customer_id=str(foreign.id))
        self.convert(lead['id'], expected=404, customer_id=str(uuid4()))
        inactive = self.customer('Inactivo', active=False)
        self.convert(lead['id'], expected=400, customer_id=str(inactive.id))
        self.assertEqual(CustomerModel.objects.filter(company_id=self.company.id).count(), 1)

    def test_open_opportunities_receive_customer(self):  # AC-05
        lead = self.create('Ana')
        board = BoardModel.objects.create(company_id=self.company.id, name='Ventas')
        stage = StageModel.objects.create(board=board, name='Nuevo', position=1)
        common = {'company_id': self.company.id, 'board': board, 'stage': stage, 'lead_id': lead['id'],
                  'owner_id': self.user.id, 'amount': Decimal('10.00')}
        open_one = OpportunityModel.objects.create(title='Abierta', **common)
        closed = OpportunityModel.objects.create(title='Perdida', status='lost', closed_at=timezone.now(),
                                                 lost_reason='Precio', **common)
        customer_id = self.convert(lead['id'])['customer']['id']
        open_one.refresh_from_db()
        closed.refresh_from_db()
        self.assertEqual((str(open_one.customer_id), str(open_one.lead_id)), (customer_id, lead['id']))
        self.assertIsNone(closed.customer_id)


class LeadAccessTests(LeadApiBase):
    def test_other_company_leads_are_404_and_hidden(self):  # INV-10
        other = LeadModel.objects.create(company_id=make_company('CRM B').id, name='Ajeno')
        self.create('Mío')
        base = f'{URL}{other.id}/'
        calls = [self.client.get(base), self.client.patch(base, {'name': 'x'}, format='json'),
                 self.client.post(base + 'convert/', {}, format='json')]
        self.assertEqual([c.status_code for c in calls], [404, 404, 404])
        self.assertEqual([r['name'] for r in self.client.get(URL).json()['results']], ['Mío'])
        self.assertIsNone(LeadModel.objects.get(pk=other.id).converted_customer_id)

    def test_unauthenticated_company_less_and_module_disabled(self):  # AC-09
        from django.contrib.auth import get_user_model

        from modules.modularity.infrastructure.django.models import CompanyModuleModel
        self.client.get(URL)  # siembra los módulos por defecto
        CompanyModuleModel.objects.filter(company_id=self.company.id, module_key='customers').delete()
        response = self.client.get(URL)
        self.assertEqual((response.status_code, response.json()['code']), (403, 'module_disabled'))
        user = get_user_model().objects.create_user(username='sin-empresa', password='x-Pass-123')
        authenticate(self.client, user)
        self.assertEqual(self.client.post(URL, {'name': 'X'}, format='json').status_code, 403)
        self.client.credentials()
        self.assertEqual(self.client.get(URL).status_code, 401)
