from dataclasses import replace
from uuid import uuid4

from django.test import SimpleTestCase

from modules.data_import.application.use_cases import EnqueueSalesImport, ExecuteSalesImport, PreviewSalesImport
from modules.data_import.application.ports import RunData
from modules.data_import.domain.errors import ImportRuleViolation, ImportValidationError
from modules.data_import.domain.fields import suggest_mapping
from shared.import_errors import ImportRejected

from .fakes import WAREHOUSE, FakeClock, FakeGateway, FakeRepository

HEADERS = ['Fecha', 'Producto', 'Cantidad', 'Precio', 'Nro Venta', 'Cliente', 'Proveedor', 'Costo']
ALL = {'infer_products': True, 'infer_customers': True, 'infer_inventory': True, 'infer_accounting': True,
       'warehouse_id': str(WAREHOUSE.id)}


def rows(*extra):
    return [list(r) for r in extra]


def setup(rows_, gateway=None, **options):
    repo = FakeRepository(HEADERS, rows_)
    gateway = gateway or FakeGateway()
    mapping = suggest_mapping(HEADERS)
    opts = {**ALL, **options}
    return repo, gateway, mapping, opts


def preview(repo, gateway, mapping, opts):
    return PreviewSalesImport(repo, gateway, FakeClock()).execute(repo.run.id, mapping, opts)


def execute(repo, gateway, mapping, opts, key=None):
    return ExecuteSalesImport(repo, gateway, FakeClock()).execute(repo.run.id, mapping, opts, key)


SALE = ['01/10/2026', 'Café', '5', '10', 'V1', 'Ana', 'Andina', '4']


class PreviewTests(SimpleTestCase):
    def test_preview_flags_sales_that_cannot_post_cost_when_costing_is_not_adopted(self):
        repo, gw, mapping, opts = setup(rows(SALE), gateway=FakeGateway(costing_valued=False))
        result = preview(repo, gw, mapping, opts)
        self.assertEqual((result.to_create, result.with_errors), (0, 1))
        self.assertEqual(result.problems[0].code, 'costing_not_adopted')
        repo, gw, mapping, opts = setup(rows(SALE), gateway=FakeGateway(costing_valued=False), infer_accounting=False)
        self.assertEqual(preview(repo, gw, mapping, opts).to_create, 1)

    def test_preview_counts_new_entities_and_purchases_without_writing(self):
        repo, gw, mapping, opts = setup(rows(SALE))
        result = preview(repo, gw, mapping, opts)
        self.assertEqual((result.to_create, result.new_products, result.new_customers), (1, 1, 1))
        self.assertEqual((result.purchases_to_create, result.units_to_buy), (1, 5))
        self.assertEqual((gw.created_products, gw.purchases, gw.sales), ([], [], []))

    def test_without_inference_missing_product_and_customer_are_errors(self):
        repo, gw, mapping, opts = setup(rows(SALE), infer_products=False, infer_customers=False)
        result = preview(repo, gw, mapping, opts)
        self.assertEqual(result.with_errors, 1)
        self.assertEqual({p.code for p in result.problems}, {'product_missing', 'customer_missing'})

    def test_missing_cost_with_shortfall_is_error(self):
        repo, gw, mapping, opts = setup(rows(['01/10/2026', 'Café', '5', '10', 'V1', '', '', '']))
        result = preview(repo, gw, mapping, opts)
        self.assertEqual(result.problems[0].code, 'cost_missing')

    def test_existing_stock_avoids_purchase(self):
        gw = FakeGateway(products=[('cafe', True)])
        gw.stock[gw.products['cafe'].id] = 10
        repo, gw, mapping, opts = setup(rows(SALE), gw)
        self.assertEqual(preview(repo, gw, mapping, opts).purchases_to_create, 0)

    def test_uncovered_date_counts_without_posting(self):
        repo, gw, mapping, opts = setup(rows(SALE), FakeGateway(covered=False))
        self.assertEqual(preview(repo, gw, mapping, opts).without_posting, 1)

    def test_disabled_modules_reject_options(self):
        repo, gw, mapping, opts = setup(rows(SALE), FakeGateway(accounting=False))
        with self.assertRaises(ImportValidationError) as ctx:
            preview(repo, gw, mapping, opts)
        self.assertIn('options.infer_accounting', ctx.exception.errors)


class ExecuteTests(SimpleTestCase):
    def test_requires_matching_preview(self):
        repo, gw, mapping, opts = setup(rows(SALE))
        with self.assertRaises(ImportRuleViolation) as ctx:
            execute(repo, gw, mapping, opts)
        self.assertEqual(ctx.exception.code, 'preview_required')
        preview(repo, gw, mapping, opts)
        with self.assertRaises(ImportRuleViolation) as ctx:
            execute(repo, gw, mapping, {**opts, 'infer_customers': False})
        self.assertEqual(ctx.exception.code, 'preview_stale')

    def test_one_paid_purchase_per_supplier_and_day_covers_all_sales_of_the_day(self):
        repo, gw, mapping, opts = setup(rows(
            ['01/10/2026', 'Café', '3', '10', 'V1', 'Ana', 'Andina', '4'],
            ['01/10/2026', 'Café', '2', '10', 'V2', 'Luis', 'Andina', '4'],
            ['01/10/2026', 'Té', '1', '5', 'V3', 'Luis', 'Andina', '2'],
            ['02/10/2026', 'Café', '1', '10', 'V4', 'Ana', 'Andina', '4']),
            default_payment_method='QR')
        preview_result = preview(repo, gw, mapping, opts)
        self.assertEqual((preview_result.purchases_to_create, preview_result.units_to_buy), (2, 7))
        execute(repo, gw, mapping, opts)
        self.assertEqual(len(gw.purchases), 2)  # día 1 (café + té), día 2 (café)
        first_day = {qty for _pid, qty, _cost in gw.purchases[0][2]}
        self.assertEqual(first_day, {5, 1})
        self.assertEqual(gw.purchase_payments, ['QR', 'QR'])  # compras pagadas con el método elegido
        self.assertEqual(len(gw.sales), 4)

    def test_cost_missing_blocks_only_the_sales_with_that_product(self):
        repo, gw, mapping, opts = setup(rows(
            ['01/10/2026', 'Café', '3', '10', 'V1', 'Ana', 'Andina', ''],
            ['01/10/2026', 'Té', '1', '5', 'V2', 'Luis', 'Andina', '2']))
        preview(repo, gw, mapping, opts)
        run = execute(repo, gw, mapping, opts)
        self.assertEqual((run.counts['created'], run.counts['failed']), (1, 1))
        self.assertEqual(len(gw.purchases), 1)  # solo se compra el té

    def test_creates_purchase_for_shortfall_then_sale_at_file_price_and_date(self):
        repo, gw, mapping, opts = setup(rows(SALE))
        preview(repo, gw, mapping, opts)
        run = execute(repo, gw, mapping, opts)
        self.assertEqual((run.status, run.counts['created']), ('COMPLETED', 1))
        self.assertEqual(len(gw.purchases), 1)
        self.assertEqual(gw.purchases[0][2][0][1:], (5, gw.purchases[0][2][0][2]))
        self.assertEqual(str(gw.sales[0]['lines'][0].unit_price), '10.00')
        self.assertEqual(gw.sales[0]['method'], 'CASH')

    def test_failed_sale_is_reported_and_others_continue(self):
        repo, gw, mapping, opts = setup(rows(SALE, ['02/10/2026', 'Té', '1', '3', 'V2', '', 'Andina', '1']))
        preview(repo, gw, mapping, opts)
        original = gw.deliver_sale
        calls = []

        def flaky(*args, **kwargs):
            calls.append(1)
            if len(calls) == 1:
                raise ImportRejected('insufficient_stock', 'No alcanza.')
            return original(*args, **kwargs)
        gw.deliver_sale = flaky
        run = execute(repo, gw, mapping, opts)
        self.assertEqual((run.counts['created'], run.counts['failed']), (1, 1))
        failed = [r for r in repo.results if r[2] == 'FAILED'][0]
        self.assertEqual((failed[3], failed[4]), ('insufficient_stock', 'No alcanza.'))

    def test_already_imported_sales_are_skipped(self):
        repo, gw, mapping, opts = setup(rows(SALE))
        repo.keys.add('n:v1')
        preview(repo, gw, mapping, opts)
        run = execute(repo, gw, mapping, opts)
        self.assertEqual((run.counts['skipped'], run.counts['created'], gw.sales), (1, 0, []))

    def test_completed_run_returns_stored_result(self):
        repo, gw, mapping, opts = setup(rows(SALE))
        preview(repo, gw, mapping, opts)
        execute(repo, gw, mapping, opts)
        again = execute(repo, gw, mapping, opts)
        self.assertEqual((again.status, len(gw.sales)), ('COMPLETED', 1))

    def test_running_import_is_rejected(self):
        repo, gw, mapping, opts = setup(rows(SALE))
        preview(repo, gw, mapping, opts)
        repo.running = True
        with self.assertRaises(ImportRuleViolation) as ctx:
            execute(repo, gw, mapping, opts)
        self.assertEqual(ctx.exception.code, 'import_running')

    def test_uncovered_sale_is_marked_without_posting(self):
        repo, gw, mapping, opts = setup(rows(SALE), FakeGateway(covered=False))
        preview(repo, gw, mapping, opts)
        run = execute(repo, gw, mapping, opts)
        self.assertEqual(run.counts['without_posting'], 1)
        self.assertEqual(repo.results[-1][2], 'CREATED_WITHOUT_POSTING')

    def test_accounting_unchecked_posts_nothing(self):
        repo, gw, mapping, opts = setup(rows(SALE), infer_accounting=False)
        preview(repo, gw, mapping, opts)
        execute(repo, gw, mapping, opts)
        self.assertFalse(gw.sales[0]['post'])
        self.assertFalse(gw.purchases[0][3])


def enqueue(repo, gateway, mapping, opts, key=None):
    return EnqueueSalesImport(repo, gateway, FakeClock()).execute(repo.run.id, mapping, opts, key)


class EnqueueTests(SimpleTestCase):
    def test_enqueue_queues_without_loading_any_sale(self):  # AC-01
        repo, gw, mapping, opts = setup(rows(SALE))
        preview(repo, gw, mapping, opts)
        run = enqueue(repo, gw, mapping, opts, uuid4())
        self.assertEqual((run.status, len(gw.sales), repo.results), ('QUEUED', 0, []))

    def test_enqueue_keeps_the_preview_checks(self):  # AC-01
        repo, gw, mapping, opts = setup(rows(SALE))
        with self.assertRaises(ImportRuleViolation) as ctx:
            enqueue(repo, gw, mapping, opts)
        self.assertEqual(ctx.exception.code, 'preview_required')
        preview(repo, gw, mapping, opts)
        with self.assertRaises(ImportRuleViolation) as ctx:
            enqueue(repo, gw, mapping, {**opts, 'infer_customers': False})
        self.assertEqual(ctx.exception.code, 'preview_stale')

    def test_same_key_returns_the_active_run_and_another_key_is_rejected(self):  # AC-04
        repo, gw, mapping, opts = setup(rows(SALE))
        preview(repo, gw, mapping, opts)
        key = uuid4()
        enqueue(repo, gw, mapping, opts, key)
        self.assertEqual(enqueue(repo, gw, mapping, opts, key).status, 'QUEUED')
        with self.assertRaises(ImportRuleViolation) as ctx:
            enqueue(repo, gw, mapping, opts, uuid4())
        self.assertEqual(ctx.exception.code, 'import_running')

    def test_another_active_run_of_the_company_rejects_the_enqueue(self):  # AC-04
        repo, gw, mapping, opts = setup(rows(SALE))
        preview(repo, gw, mapping, opts)
        repo.running = True
        with self.assertRaises(ImportRuleViolation) as ctx:
            enqueue(repo, gw, mapping, opts, uuid4())
        self.assertEqual(ctx.exception.code, 'import_running')

    def test_completed_run_returns_its_stored_result(self):
        repo, gw, mapping, opts = setup(rows(SALE))
        preview(repo, gw, mapping, opts)
        execute(repo, gw, mapping, opts)
        self.assertEqual(enqueue(repo, gw, mapping, opts).status, 'COMPLETED')


class RunClaimedTests(SimpleTestCase):
    def _claimed(self, rows_, **options):
        repo, gw, mapping, opts = setup(rows_, **options)
        preview(repo, gw, mapping, opts)
        enqueue(repo, gw, mapping, opts, uuid4())
        repo.run = RunData(**{**repo.run.__dict__, 'status': 'RUNNING'})  # lo que hace el worker al reclamar
        return repo, gw

    def test_worker_run_loads_sales_like_the_synchronous_path_and_reports_progress(self):  # AC-02, AC-03
        repo, gw = self._claimed(rows(SALE, ['02/10/2026', 'Café', '1', '10', 'V2', 'Ana', 'Andina', '4']))
        run = ExecuteSalesImport(repo, gw, FakeClock()).run_claimed(repo.run.id)
        self.assertEqual((run.status, run.counts['created'], len(gw.sales)), ('COMPLETED', 2, 2))
        self.assertEqual(repo.progress, [(0, 2), (1, 2), (2, 2)])

    def test_revalidation_failure_ends_failed_with_a_reason(self):  # AC-05
        repo, gw = self._claimed(rows(SALE))
        gw.caps = replace(gw.caps, customers=False)  # el módulo se deshabilitó entre el encolado y la ejecución
        run = ExecuteSalesImport(repo, gw, FakeClock()).run_claimed(repo.run.id)
        self.assertEqual(run.status, 'FAILED')
        self.assertTrue(run.failure_code)
        self.assertEqual(len(gw.sales), 0)

    def test_unexpected_error_ends_failed_and_is_not_raised(self):  # AC-05
        repo, gw = self._claimed(rows(SALE))

        def boom(*args, **kwargs):
            raise RuntimeError('boom')

        repo.existing_keys = boom
        run = ExecuteSalesImport(repo, gw, FakeClock()).run_claimed(repo.run.id)
        self.assertEqual((run.status, run.failure_code), ('FAILED', 'unexpected_error'))
