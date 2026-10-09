from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from django.test import SimpleTestCase

from modules.expenses.domain.category import ExpenseCategory
from modules.expenses.domain.enums import ExpenseStatus, PaymentMethod
from modules.expenses.domain.exceptions import ExpenseRuleViolation, ExpenseValidationError
from modules.expenses.domain.expense import Expense

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


def make_expense(**overrides) -> Expense:
    values = dict(description='Harina', amount=Decimal('120.50'), category_id=uuid4(), expense_date=date(2026, 10, 1))
    values.update(overrides)
    return Expense.create(**values)


class ExpenseCreationTests(SimpleTestCase):
    def test_creates_a_valid_expense_with_defaults(self):  # AC-03, INV-03
        category_id = uuid4()
        expense = make_expense(category_id=category_id)
        self.assertEqual(expense.amount, Decimal('120.50'))
        self.assertEqual(expense.payment_method, PaymentMethod.CASH)
        self.assertEqual(expense.status, ExpenseStatus.ACTIVE)
        self.assertEqual((expense.supplier_name, expense.notes), ('', ''))
        self.assertEqual(expense.category_id, category_id)
        self.assertIsNone(expense.voided_at)

    def test_trims_texts_and_accepts_string_amount(self):
        expense = make_expense(description='  Harina  ', amount='10', supplier_name=' Molino ', notes=' n ')
        self.assertEqual((expense.description, expense.amount), ('Harina', Decimal('10.00')))
        self.assertEqual((expense.supplier_name, expense.notes), ('Molino', 'n'))

    def test_rejects_zero_negative_and_invalid_amounts(self):  # AC-04, INV-01, EDGE-01
        for bad in (0, '0', Decimal('0.00'), -1, '-5.00', '0.001', 'abc', True, 12.5, None, '10000000000.00',
                    '1e3', '1E3', '1_000', ' 1e3 ', '+5', '1e-7', 'Infinity', 'NaN', '', '1,5', '١٢'):
            with self.subTest(amount=bad):
                with self.assertRaises(ExpenseValidationError) as ctx:
                    make_expense(amount=bad)
                self.assertEqual(list(ctx.exception.errors), ['amount'])

    def test_accepts_plain_decimal_texts_and_numbers(self):  # EDGE-01
        for good, expected in (('10', '10.00'), (' 45.50 ', '45.50'), ('120.5', '120.50'), (1000, '1000.00'),
                               (Decimal('0.01'), '0.01')):
            with self.subTest(amount=good):
                self.assertEqual(make_expense(amount=good).amount, Decimal(expected))

    def test_invalid_amount_does_not_hide_the_other_errors(self):  # AC-04, EDGE-01
        with self.assertRaises(ExpenseValidationError) as ctx:
            Expense.create(description='', amount='1e3', category_id=None, expense_date=None)
        self.assertEqual(set(ctx.exception.errors), {'description', 'amount', 'category_id', 'expense_date'})

    def test_requires_description_date_and_category(self):  # AC-04, INV-02
        with self.assertRaises(ExpenseValidationError) as ctx:
            Expense.create(description='  ', amount='5', category_id=None, expense_date=None)
        self.assertEqual(set(ctx.exception.errors), {'description', 'category_id', 'expense_date'})

    def test_accumulates_errors_from_all_fields(self):
        with self.assertRaises(ExpenseValidationError) as ctx:
            Expense.create(description='', amount=0, category_id=uuid4(), expense_date=date(2026, 1, 1),
                           payment_method='CHEQUE')
        self.assertEqual(set(ctx.exception.errors), {'description', 'amount', 'payment_method'})

    def test_enforces_maximum_lengths(self):  # INV-02
        for field, size in (('description', 201), ('supplier_name', 151), ('notes', 2001)):
            with self.subTest(field=field):
                with self.assertRaises(ExpenseValidationError) as ctx:
                    make_expense(**{field: 'x' * size})
                self.assertEqual(list(ctx.exception.errors), [field])

    def test_payment_method_accepts_the_five_codes_and_rejects_others(self):  # AC-09, INV-03
        for code in ('CASH', 'QR', 'BANK_TRANSFER', 'CARD', 'OTHER'):
            self.assertEqual(make_expense(payment_method=code).payment_method, PaymentMethod(code))
        self.assertEqual(make_expense(payment_method='').payment_method, PaymentMethod.CASH)
        with self.assertRaises(ExpenseValidationError):
            make_expense(payment_method='cheque')

    def test_a_datetime_is_not_a_date(self):
        with self.assertRaises(ExpenseValidationError) as ctx:
            make_expense(expense_date=NOW)
        self.assertEqual(list(ctx.exception.errors), ['expense_date'])


class ExpenseUpdateTests(SimpleTestCase):
    def test_partial_update_keeps_unsent_fields(self):  # AC-06
        expense = make_expense()
        original_category = expense.category_id
        expense.update(amount='99.99')
        self.assertEqual(expense.amount, Decimal('99.99'))
        self.assertEqual((expense.description, expense.category_id), ('Harina', original_category))

    def test_update_applies_the_same_validations_as_creation(self):  # AC-06
        expense = make_expense()
        with self.assertRaises(ExpenseValidationError) as ctx:
            expense.update(amount=0, description='')
        self.assertEqual(set(ctx.exception.errors), {'amount', 'description'})
        self.assertEqual(expense.amount, Decimal('120.50'))  # no quedó a medias

    def test_update_can_clear_optional_fields(self):
        expense = make_expense(supplier_name='X', notes='Y')
        expense.update(supplier_name=None, notes='')
        self.assertEqual((expense.supplier_name, expense.notes), ('', ''))

    def test_cannot_update_a_voided_expense(self):  # AC-07, INV-05
        expense = make_expense()
        expense.void(NOW)
        with self.assertRaises(ExpenseRuleViolation) as ctx:
            expense.update(amount='5')
        self.assertEqual(ctx.exception.code, 'expense_voided')


class ExpenseVoidTests(SimpleTestCase):
    def test_void_marks_the_expense_and_records_when(self):  # AC-07
        expense = make_expense()
        expense.void(NOW)
        self.assertEqual((expense.status, expense.voided_at), (ExpenseStatus.VOIDED, NOW))
        self.assertTrue(expense.voided)

    def test_void_is_irreversible_and_not_repeatable(self):  # INV-05
        expense = make_expense()
        expense.void(NOW)
        with self.assertRaises(ExpenseRuleViolation) as ctx:
            expense.void(NOW)
        self.assertEqual(ctx.exception.code, 'already_voided')


class ExpenseCategoryTests(SimpleTestCase):
    def test_creates_an_active_category_with_trimmed_name(self):  # AC-01
        category = ExpenseCategory.create('  Empaque ')
        self.assertEqual((category.name, category.active), ('Empaque', True))

    def test_name_is_required_and_limited(self):  # AC-01, INV-06
        for bad in (None, '', '   ', 5):
            with self.assertRaises(ExpenseValidationError):
                ExpenseCategory.create(bad)
        with self.assertRaises(ExpenseValidationError) as ctx:
            ExpenseCategory.create('x' * 101)
        self.assertEqual(list(ctx.exception.errors), ['name'])

    def test_rename_activate_and_deactivate(self):  # AC-02
        category = ExpenseCategory.create('Empaque')
        category.rename('Embalaje')
        category.deactivate()
        category.deactivate()  # idempotente
        self.assertEqual((category.name, category.active), ('Embalaje', False))
        category.activate()
        self.assertTrue(category.active)

    def test_failed_rename_keeps_the_name(self):
        category = ExpenseCategory.create('Empaque')
        with self.assertRaises(ExpenseValidationError):
            category.rename(' ')
        self.assertEqual(category.name, 'Empaque')
