import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { environment } from '../../../../environments/environment';
import { ImportApiError, ImportMapping, ImportRequest } from '../models/sales-import';
import { SalesImportApiService } from './sales-import-api.service';

const MAPPING: ImportMapping = {
  sale_date: 'Fecha',
  product_name: 'Producto',
  quantity: 'Cant',
  unit_price: 'Precio',
  sale_number: null,
  customer_name: null,
  payment_method: null,
  sales_channel: null,
  supplier_name: null,
  unit_cost: null,
  discount: null,
  notes: null,
};

const REQUEST: ImportRequest = {
  mapping: MAPPING,
  options: {
    inferProducts: true,
    inferCustomers: false,
    inferInventory: false,
    inferAccounting: true,
    defaultPaymentMethod: 'CASH',
    defaultSalesChannel: 'OTHER',
    warehouseId: null,
    dateFormat: 'dmy',
  },
};

describe('SalesImportApiService', () => {
  let service: SalesImportApiService;
  let http: HttpTestingController;
  const base = `${environment.apiUrl}/imports/sales/`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(SalesImportApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('uploads the file as multipart and maps the response', () => {
    const file = new File(['a,b'], 'ventas.csv', { type: 'text/csv' });
    let id = '';
    service.upload(file).subscribe((u) => {
      id = u.id;
      expect(u.rowCount).toBe(2);
      expect(u.capabilities.warehouses[0].isDefault).toBeTrue();
      expect(u.capabilities.paymentMethods).toEqual(['CASH']);
    });
    const req = http.expectOne(base);
    expect(req.request.method).toBe('POST');
    expect((req.request.body as FormData).get('file')).toBe(file);
    req.flush({
      id: 'r-1',
      filename: 'ventas.csv',
      row_count: 2,
      headers: ['Fecha'],
      sample_rows: [['1']],
      suggested_mapping: MAPPING,
      capabilities: {
        customers: true,
        inventory: true,
        purchases: true,
        accounting: true,
        costing: true,
        warehouses: [{ id: 'w-1', name: 'Central', is_default: true }],
        payment_methods: ['CASH'],
        sales_channels: ['OTHER'],
      },
    });
    expect(id).toBe('r-1');
  });

  it('sends the mapping and options in snake_case on preview and adds the idempotency key on execute', () => {
    service.preview('r-1', REQUEST).subscribe();
    const preview = http.expectOne(`${base}r-1/preview/`);
    expect(preview.request.body).toEqual({
      mapping: MAPPING,
      options: {
        infer_products: true,
        infer_customers: false,
        infer_inventory: false,
        infer_accounting: true,
        default_payment_method: 'CASH',
        default_sales_channel: 'OTHER',
        warehouse_id: null,
        date_format: 'dmy',
      },
    });
    preview.flush({
      sales_total: 1, lines_total: 2, to_create: 1, already_imported: 0, with_errors: 0, new_products: 1,
      existing_products: 0, new_customers: 0, existing_customers: 0, purchases_to_create: 0, units_to_buy: 0,
      without_posting: 0, problems: [{ row: 3, sale_key: 'V1', field: 'quantity', code: 'x', message: 'm' }],
      problems_total: 1,
    });

    let counts = '';
    service.execute('r-1', REQUEST, 'key-1').subscribe((r) => (counts = JSON.stringify(r.counts)));
    const execute = http.expectOne(`${base}r-1/execute/`);
    expect((execute.request.body as { idempotency_key: string }).idempotency_key).toBe('key-1');
    execute.flush({ id: 'r-1', status: 'COMPLETED', counts: { created: 1, skipped: 0, failed: 0, without_posting: 2 } });
    expect(JSON.parse(counts)).toEqual({ created: 1, skipped: 0, failed: 0, withoutPosting: 2 });
  });

  it('maps 400 to field errors, 409 import_running to its code and 409 posting issues', () => {
    let error: ImportApiError | null = null;
    service.preview('r-1', REQUEST).subscribe({ error: (e: ImportApiError) => (error = e) });
    http.expectOne(`${base}r-1/preview/`).flush({ mapping: ['Falta la columna'] }, { status: 400, statusText: 'Bad' });
    expect(error!.status).toBe(400);
    expect(error!.fieldMessages).toEqual(['Falta la columna']);

    service.execute('r-1', REQUEST, 'k').subscribe({ error: (e: ImportApiError) => (error = e) });
    http.expectOne(`${base}r-1/execute/`).flush({ code: 'import_running', detail: 'En curso' }, { status: 409, statusText: 'C' });
    expect(error!.code).toBe('import_running');
    expect(error!.message).toBe('En curso');

    service.execute('r-1', REQUEST, 'k').subscribe({ error: (e: ImportApiError) => (error = e) });
    http.expectOne(`${base}r-1/execute/`).flush(
      { code: 'posting_configuration_missing', detail: 'Falta', issues: [{ code: 'a', subject: 's', message: 'm' }] },
      { status: 409, statusText: 'C' },
    );
    expect(error!.issues.length).toBe(1);
  });

  it('maps a network failure', () => {
    let error: ImportApiError | null = null;
    service.get('r-1').subscribe({ error: (e: ImportApiError) => (error = e) });
    http.expectOne(`${base}r-1/`).error(new ProgressEvent('error'));
    expect(error!.status).toBe(0);
  });

  it('lists runs, reads rows with filters and downloads the template as a blob', () => {
    service.list(2).subscribe((p) => expect(p.results[0].counts.withoutPosting).toBe(1));
    const list = http.expectOne((r) => r.url === base);
    expect(list.request.params.get('page')).toBe('2');
    list.flush({
      count: 1, next: null, previous: null,
      results: [{ id: 'r', filename: 'f', status: 'COMPLETED', created_at: 'd', created_by_name: 'ana', row_count: 1,
        counts: { created: 1, skipped: 0, failed: 0, without_posting: 1 } }],
    });

    service.rows('r', 'FAILED', 3).subscribe((p) => expect(p.results[0].orderId).toBeNull());
    const rows = http.expectOne((r) => r.url === `${base}r/rows/`);
    expect(rows.request.params.get('status')).toBe('FAILED');
    expect(rows.request.params.get('page')).toBe('3');
    rows.flush({ count: 1, next: null, previous: null, results: [
      { row: 2, sale_key: 'V', status: 'FAILED', code: 'c', message: 'm', order_id: null }] });

    service.template().subscribe((blob) => expect(blob.size).toBeGreaterThan(0));
    const tpl = http.expectOne(`${base}template/`);
    expect(tpl.request.responseType).toBe('blob');
    tpl.flush(new Blob(['a,b']));
  });
});
