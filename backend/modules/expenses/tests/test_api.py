from uuid import uuid4

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase

from modules.expenses.infrastructure.django.models import ExpenseCategoryModel

EXPENSES = '/api/expenses/'
CATEGORIES = '/api/expense-categories/'

EXPENSE_KEYS = {
    'id', 'description', 'amount', 'expense_date', 'category', 'payment_method', 'supplier_name', 'notes', 'status',
    'voided_at', 'created_at', 'updated_at',
}


class ExpensesApiTestCase(APITestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username='ana', password='x-Pass-123')
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def category(self, name='Empaque', expected_status=201):
        response = self.client.post(CATEGORIES, {'name': name}, format='json')
        self.assertEqual(response.status_code, expected_status, response.content)
        return response.json()

    def expense(self, category=None, expected_status=201, **extra):
        category = category or self.category(f'Cat {uuid4().hex[:6]}')
        body = {'description': 'Harina', 'amount': '50.00', 'category_id': category['id'],
                'expense_date': '2026-10-05', **extra}
        response = self.client.post(EXPENSES, body, format='json')
        self.assertEqual(response.status_code, expected_status, response.content)
        return response.json()

    def void(self, expense, expected_status=200):
        response = self.client.post(f'{EXPENSES}{expense["id"]}/void/')
        self.assertEqual(response.status_code, expected_status, response.content)
        return response.json()


class AuthenticationTests(APITestCase):
    def test_every_route_requires_authentication(self):  # AC-19
        anyone = uuid4()
        for method, path in (
            ('get', EXPENSES), ('post', EXPENSES), ('get', f'{EXPENSES}{anyone}/'), ('patch', f'{EXPENSES}{anyone}/'),
            ('post', f'{EXPENSES}{anyone}/void/'), ('get', CATEGORIES), ('post', CATEGORIES),
            ('get', f'{CATEGORIES}{anyone}/'), ('patch', f'{CATEGORIES}{anyone}/'),
            ('post', f'{CATEGORIES}{anyone}/activate/'), ('post', f'{CATEGORIES}{anyone}/deactivate/'),
        ):
            with self.subTest(method=method, path=path):
                self.assertEqual(getattr(APIClient(), method)(path).status_code, 401)


class CategoryApiTests(ExpensesApiTestCase):
    def test_creates_a_category_available_for_expenses(self):  # AC-01
        created = self.category('Empaque')
        self.assertEqual((created['name'], created['active']), ('Empaque', True))
        listed = self.client.get(CATEGORIES, {'active': 'true'}).json()
        self.assertEqual([c['name'] for c in listed['results']], ['Empaque'])

    def test_name_is_required_and_unique_ignoring_case(self):  # AC-01
        response = self.client.post(CATEGORIES, {'name': ' '}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('name', response.json())
        self.category('Empaque')
        response = self.client.post(CATEGORIES, {'name': 'empaque'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'name': ['Ya existe una categoría con ese nombre.']})

    def test_missing_body_is_a_name_error(self):
        response = self.client.post(CATEGORIES, {}, format='json')
        self.assertEqual((response.status_code, list(response.json())), (400, ['name']))

    def test_renames_activates_and_deactivates(self):  # AC-02
        category = self.category('Empaque')
        renamed = self.client.patch(f'{CATEGORIES}{category["id"]}/', {'name': 'Embalaje'}, format='json')
        self.assertEqual((renamed.status_code, renamed.json()['name']), (200, 'Embalaje'))
        off = self.client.post(f'{CATEGORIES}{category["id"]}/deactivate/')
        self.assertEqual((off.status_code, off.json()['active']), (200, False))
        on = self.client.post(f'{CATEGORIES}{category["id"]}/activate/')
        self.assertEqual((on.status_code, on.json()['active']), (200, True))

    def test_lists_filter_by_active_and_search(self):
        a = self.category('Empaque')
        self.category('Delivery')
        self.client.post(f'{CATEGORIES}{a["id"]}/deactivate/')
        inactive = self.client.get(CATEGORIES, {'active': 'false'}).json()['results']
        self.assertEqual([c['name'] for c in inactive], ['Empaque'])
        found = self.client.get(CATEGORIES, {'search': 'deli'}).json()['results']
        self.assertEqual([c['name'] for c in found], ['Delivery'])
        self.assertEqual(self.client.get(CATEGORIES, {'active': 'quizas'}).status_code, 400)

    def test_deactivating_does_not_change_historical_expenses(self):  # AC-02
        category = self.category('Empaque')
        expense = self.expense(category)
        self.client.post(f'{CATEGORIES}{category["id"]}/deactivate/')
        detail = self.client.get(f'{EXPENSES}{expense["id"]}/').json()
        self.assertEqual(detail['category'], {'id': category['id'], 'name': 'Empaque', 'active': False})

    def test_category_cannot_be_deleted(self):  # AC-02
        category = self.category()
        self.assertEqual(self.client.delete(f'{CATEGORIES}{category["id"]}/').status_code, 405)
        self.assertTrue(ExpenseCategoryModel.objects.filter(pk=category['id']).exists())

    def test_unknown_or_malformed_ids_are_404(self):
        for path in (f'{CATEGORIES}{uuid4()}/', f'{CATEGORIES}no-es-uuid/'):
            self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.client.post(f'{CATEGORIES}{uuid4()}/deactivate/').status_code, 404)
        self.assertEqual(self.client.patch(f'{CATEGORIES}{uuid4()}/', {'name': 'x'}, format='json').status_code, 404)


class CreateExpenseApiTests(ExpensesApiTestCase):
    def test_registers_an_expense_with_the_embedded_category(self):  # AC-03
        category = self.category('Empaque')
        created = self.expense(category, description='Cajas', amount='120.50', supplier_name='Cartonera', notes='n')
        self.assertEqual(set(created), EXPENSE_KEYS)
        self.assertEqual(created['amount'], '120.50')
        self.assertEqual(created['category'], {'id': category['id'], 'name': 'Empaque', 'active': True})
        self.assertEqual((created['status'], created['voided_at']), ('ACTIVE', None))
        self.assertEqual(self.client.get(f'{EXPENSES}{created["id"]}/').json(), created)

    def test_payment_method_defaults_to_cash_and_is_returned(self):  # AC-09
        self.assertEqual(self.expense()['payment_method'], 'CASH')
        for code in ('QR', 'BANK_TRANSFER', 'CARD', 'OTHER'):
            self.assertEqual(self.expense(payment_method=code)['payment_method'], code)

    def test_invalid_payment_method_is_400(self):  # AC-09
        category = self.category()
        response = self.client.post(EXPENSES, {'description': 'x', 'amount': '5', 'category_id': category['id'],
                                               'expense_date': '2026-10-05', 'payment_method': 'CHEQUE'},
                                    format='json')
        self.assertEqual((response.status_code, list(response.json())), (400, ['payment_method']))

    def test_rejects_zero_negative_and_malformed_amounts(self):  # AC-04, EDGE-01
        category = self.category()
        for bad in ('0', '0.00', '-5', '0.001', 'abc', '10000000000.00', True, None, '1e3', '1E3', '1_000', ' 1e3', '+5',
                    '', 1e-7):
            with self.subTest(amount=bad):
                body = {'description': 'x', 'amount': bad, 'category_id': category['id'], 'expense_date': '2026-10-05'}
                response = self.client.post(EXPENSES, body, format='json')
                self.assertEqual(response.status_code, 400, response.content)
                self.assertEqual(list(response.json()), ['amount'])

    def test_accepts_plain_decimal_texts_and_json_numbers(self):  # EDGE-01
        category = self.category()
        for sent, stored in (('10', '10.00'), ('120.5', '120.50'), (1000, '1000.00'), (12.5, '12.50'), (' 45.50 ', '45.50')):
            with self.subTest(amount=sent):
                body = {'description': 'x', 'amount': sent, 'category_id': category['id'], 'expense_date': '2026-10-05'}
                response = self.client.post(EXPENSES, body, format='json')
                self.assertEqual(response.status_code, 201, response.content)
                self.assertEqual(response.json()['amount'], stored)

    def test_invalid_amount_is_reported_together_with_the_other_errors(self):  # AC-04, EDGE-01
        response = self.client.post(EXPENSES, {'amount': 'abc', 'description': ''}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {'description', 'amount', 'category_id', 'expense_date'})

    def test_scientific_notation_is_rejected_on_edit_too(self):  # EDGE-01
        expense = self.expense(amount='50.00')
        for bad in ('1e3', '1_000'):
            response = self.client.patch(f'{EXPENSES}{expense["id"]}/', {'amount': bad}, format='json')
            self.assertEqual((response.status_code, list(response.json())), (400, ['amount']))
        self.assertEqual(self.client.get(f'{EXPENSES}{expense["id"]}/').json()['amount'], '50.00')

    def test_required_fields_are_reported_together(self):  # AC-04
        response = self.client.post(EXPENSES, {}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {'description', 'amount', 'category_id', 'expense_date'})

    def test_category_must_exist_and_be_active(self):  # AC-05
        inactive = self.category('Vieja')
        self.client.post(f'{CATEGORIES}{inactive["id"]}/deactivate/')
        for category_id in (str(uuid4()), inactive['id']):
            response = self.client.post(EXPENSES, {'description': 'x', 'amount': '5', 'category_id': category_id,
                                                   'expense_date': '2026-10-05'}, format='json')
            self.assertEqual((response.status_code, list(response.json())), (400, ['category_id']))

    def test_invalid_date_is_400(self):  # AC-04
        category = self.category()
        response = self.client.post(EXPENSES, {'description': 'x', 'amount': '5', 'category_id': category['id'],
                                               'expense_date': '05/10/2026'}, format='json')
        self.assertEqual((response.status_code, list(response.json())), (400, ['expense_date']))


class UpdateExpenseApiTests(ExpensesApiTestCase):
    def test_edits_amount_category_and_date(self):  # AC-06
        a, b = self.category('A'), self.category('B')
        expense = self.expense(a)
        response = self.client.patch(f'{EXPENSES}{expense["id"]}/', {
            'amount': '75.25', 'category_id': b['id'], 'expense_date': '2026-10-07'}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual((body['amount'], body['category']['id'], body['expense_date']), ('75.25', b['id'], '2026-10-07'))
        self.assertEqual(body['description'], 'Harina')

    def test_same_validations_as_creation(self):  # AC-06
        expense = self.expense()
        response = self.client.patch(f'{EXPENSES}{expense["id"]}/', {'amount': '0', 'description': ''}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {'amount', 'description'})

    def test_can_keep_an_inactive_category_but_not_switch_to_one(self):  # AC-05
        old, other = self.category('Vieja'), self.category('Otra')
        expense = self.expense(old)
        self.client.post(f'{CATEGORIES}{old["id"]}/deactivate/')
        kept = self.client.patch(f'{EXPENSES}{expense["id"]}/', {'amount': '9.00', 'category_id': old['id']},
                                 format='json')
        self.assertEqual(kept.status_code, 200, kept.content)
        self.client.post(f'{CATEGORIES}{other["id"]}/deactivate/')
        switched = self.client.patch(f'{EXPENSES}{expense["id"]}/', {'category_id': other['id']}, format='json')
        self.assertEqual((switched.status_code, list(switched.json())), (400, ['category_id']))

    def test_editing_updates_the_reports_afterwards(self):  # AC-06
        expense = self.expense(amount='50.00')
        self.client.patch(f'{EXPENSES}{expense["id"]}/', {'amount': '80.00'}, format='json')
        self.assertEqual(self.client.get(EXPENSES).json()['total_amount'], '80.00')

    def test_unknown_expense_is_404(self):
        self.assertEqual(self.client.patch(f'{EXPENSES}{uuid4()}/', {'amount': '1'}, format='json').status_code, 404)
        self.assertEqual(self.client.get(f'{EXPENSES}no-es-uuid/').status_code, 404)


class VoidExpenseApiTests(ExpensesApiTestCase):
    def test_voids_an_expense_and_it_stops_adding_up(self):  # AC-07
        keep = self.expense(amount='30.00')
        gone = self.expense(amount='20.00')
        voided = self.void(gone)
        self.assertEqual(voided['status'], 'VOIDED')
        self.assertIsNotNone(voided['voided_at'])
        listing = self.client.get(EXPENSES).json()
        self.assertEqual([e['id'] for e in listing['results']], [keep['id']])
        self.assertEqual(listing['total_amount'], '30.00')

    def test_voiding_twice_is_409(self):  # AC-07
        expense = self.expense()
        self.void(expense)
        response = self.client.post(f'{EXPENSES}{expense["id"]}/void/')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'already_voided')

    def test_editing_a_voided_expense_is_409(self):  # AC-07
        expense = self.expense()
        self.void(expense)
        response = self.client.patch(f'{EXPENSES}{expense["id"]}/', {'amount': '1.00'}, format='json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'expense_voided')

    def test_there_is_no_delete(self):  # AC-07
        expense = self.expense()
        self.assertEqual(self.client.delete(f'{EXPENSES}{expense["id"]}/').status_code, 405)
        self.assertEqual(self.client.get(f'{EXPENSES}{expense["id"]}/').status_code, 200)

    def test_unknown_expense_is_404(self):
        self.assertEqual(self.client.post(f'{EXPENSES}{uuid4()}/void/').status_code, 404)


class ListExpensesApiTests(ExpensesApiTestCase):
    def setUp(self):
        super().setUp()
        self.a, self.b = self.category('A'), self.category('B')
        self.e1 = self.expense(self.a, amount='10.00', expense_date='2026-09-30')
        self.e2 = self.expense(self.a, amount='20.00', expense_date='2026-10-05')
        self.e3 = self.expense(self.b, amount='30.00', expense_date='2026-10-31')
        self.e4 = self.expense(self.b, amount='40.00', expense_date='2026-10-10')
        self.void(self.e4)

    def ids(self, **params):
        return [e['id'] for e in self.client.get(EXPENSES, params).json()['results']]

    def test_defaults_to_active_expenses_newest_first(self):  # AC-08
        self.assertEqual(self.ids(), [self.e3['id'], self.e2['id'], self.e1['id']])

    def test_month_range_is_inclusive_and_can_be_limited_to_a_category(self):  # AC-08
        month = {'date_from': '2026-10-01', 'date_to': '2026-10-31'}
        self.assertEqual(self.ids(**month), [self.e3['id'], self.e2['id']])
        self.assertEqual(self.ids(category_id=self.b['id'], **month), [self.e3['id']])

    def test_status_filter(self):  # AC-08
        self.assertEqual(self.ids(status='voided'), [self.e4['id']])
        self.assertEqual(len(self.ids(status='all')), 4)

    def test_total_amount_sums_active_expenses_of_the_filter_across_pages(self):  # AC-08, INV-07
        data = self.client.get(EXPENSES, {'page_size': 1}).json()
        self.assertEqual((data['count'], len(data['results']), data['total_amount']), (3, 1, '60.00'))
        month = self.client.get(EXPENSES, {'date_from': '2026-10-01', 'date_to': '2026-10-31'}).json()
        self.assertEqual(month['total_amount'], '50.00')

    def test_total_ignores_the_status_filter_and_is_zero_when_empty(self):  # AC-08
        self.assertEqual(self.client.get(EXPENSES, {'status': 'voided'}).json()['total_amount'], '60.00')
        empty = self.client.get(EXPENSES, {'date_from': '2030-01-01'}).json()
        self.assertEqual((empty['results'], empty['total_amount']), ([], '0.00'))

    def test_list_rows_carry_the_category_and_payment_method(self):
        row = self.client.get(EXPENSES).json()['results'][0]
        self.assertEqual(row['category']['name'], 'B')
        self.assertEqual(row['payment_method'], 'CASH')
        self.assertNotIn('notes', row)

    def test_invalid_parameters_are_400_per_parameter(self):  # AC-08
        for params, field in (
            ({'date_from': 'ayer'}, 'date_from'), ({'date_to': '2026-13-01'}, 'date_to'),
            ({'category_id': 'x'}, 'category_id'), ({'status': 'otro'}, 'status'),
            ({'date_from': '2026-10-02', 'date_to': '2026-10-01'}, 'date_to'),
        ):
            with self.subTest(params=params):
                response = self.client.get(EXPENSES, params)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(list(response.json()), [field])
