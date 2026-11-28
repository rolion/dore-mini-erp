import { HttpErrorResponse, provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideTestTranslations } from '../../core/i18n/testing';
import { DocumentReportApiService } from './document-report-api.service';

const FILTERS = { dateFrom: '2026-01-01', dateTo: '2026-03-31', fiscalPeriodId: 'p1' };

describe('DocumentReportApiService', () => {
  let service: DocumentReportApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(DocumentReportApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('sends filters and paging as query params and maps the page (AC-02, AC-03, AC-04)', () => {
    let result: unknown;
    service.list('paid', FILTERS, 2, 10).subscribe((page) => (result = page));
    const req = http.expectOne((r) => r.url.endsWith('/orders/paid-report/'));
    expect(req.request.params.get('date_from')).toBe('2026-01-01');
    expect(req.request.params.get('date_to')).toBe('2026-03-31');
    expect(req.request.params.get('fiscal_period_id')).toBe('p1');
    expect(req.request.params.get('page')).toBe('2');
    expect(req.request.params.get('page_size')).toBe('10');
    req.flush({
      count: 1,
      results: [{ id: 'o1', code: 'PED-1', order_date: '2026-02-01', customer: { id: 'c1', name: 'Ana' }, total: '10.00', balance: '0.00' }],
      totals: { orders_count: 1, total: '10.00', balance: '0.00' },
    });
    expect(result).toEqual({
      count: 1,
      rows: [{ id: 'o1', code: 'PED-1', orderDate: '2026-02-01', customerName: 'Ana', total: '10.00', balance: '0.00' }],
      totals: { ordersCount: 1, total: '10.00', balance: '0.00' },
    });
  });

  it('maps the dental report with doctor, amount and the plain count total (AC-10)', () => {
    let result: unknown;
    service.list('dental-paid', { dateFrom: '2026-11-01', dateTo: '', fiscalPeriodId: '' }, 1, 10).subscribe((page) => (result = page));
    const req = http.expectOne((r) => r.url.endsWith('/dentistry/reports/proformas/paid/'));
    expect(req.request.params.get('date_from')).toBe('2026-11-01');
    req.flush({
      count: 1,
      results: [{ id: 'p1', code: 'ODO-000001', order_date: '2026-11-04', customer: { id: 'c1', name: 'Rosa' },
        doctor: { id: 'd1', name: 'Dra. Paz' }, amount: '100.00' }],
      totals: { count: 1, amount: '100.00' },
    });
    expect(result).toEqual({
      count: 1,
      rows: [{ id: 'p1', code: 'ODO-000001', orderDate: '2026-11-04', customerName: 'Rosa', total: '0.00', balance: '0.00',
        doctorName: 'Dra. Paz', amount: '100.00' }],
      totals: { ordersCount: 1, total: '0.00', balance: '0.00', amount: '100.00' },
    });
    service.export('dental-paid', 'xlsx', { dateFrom: '', dateTo: '', fiscalPeriodId: '' }).subscribe();
    http.expectOne((r) => r.url.endsWith('/dentistry/reports/proformas/paid/export/xlsx/')).flush(new Blob(['x']));
  });

  it('omits empty filters', () => {
    service.list('paid', { dateFrom: '', dateTo: '', fiscalPeriodId: '' }, 1, 10).subscribe();
    const req = http.expectOne((r) => r.url.endsWith('/orders/paid-report/'));
    expect(req.request.params.has('date_from')).toBeFalse();
    expect(req.request.params.has('fiscal_period_id')).toBeFalse();
    req.flush({ count: 0, results: [], totals: { orders_count: 0, total: '0.00', balance: '0.00' } });
  });

  it('turns a server error into an Error with its message', () => {
    let message = '';
    service.list('paid', FILTERS, 1, 10).subscribe({ error: (err: Error) => (message = err.message) });
    http.expectOne((r) => r.url.endsWith('/orders/paid-report/')).flush({ date_to: ['Rango inválido.'] }, { status: 400, statusText: 'Bad' });
    expect(message).toBe('Rango inválido.');
  });

  it('downloads each format as a blob with the same filters (AC-05)', () => {
    for (const format of ['pdf', 'xlsx'] as const) {
      let blob: Blob | undefined;
      service.export('paid', format, FILTERS).subscribe((b) => (blob = b));
      const req = http.expectOne((r) => r.url.endsWith(`/orders/paid-report/export/${format}/`));
      expect(req.request.responseType).toBe('blob');
      expect(req.request.params.get('fiscal_period_id')).toBe('p1');
      req.flush(new Blob(['x']));
      expect(blob).toBeDefined();
    }
  });

  it('reports the row limit on a 400 export', () => {
    let error: unknown;
    service.export('paid', 'pdf', FILTERS).subscribe({ error: (err: unknown) => (error = err) });
    http.expectOne((r) => r.url.includes('/export/pdf/')).error(new ProgressEvent('x'), { status: 400 } as Partial<HttpErrorResponse>);
    expect((error as Error).message).toContain('demasiados pedidos');
  });

  it('uses the receivable endpoints for the receivable report (AC-05)', () => {
    service.list('receivable', FILTERS, 1, 10).subscribe();
    http.expectOne((r) => r.url.endsWith('/orders/receivable-report/')).flush({ count: 0, results: [], totals: { orders_count: 0, total: '0.00', balance: '0.00' } });
    service.export('receivable', 'xlsx', FILTERS).subscribe();
    http.expectOne((r) => r.url.endsWith('/orders/receivable-report/export/xlsx/')).flush(new Blob(['x']));
  });

  it('uses the purchases endpoints for the purchase reports (AC-05)', () => {
    for (const [kind, path] of [['purchases-paid', 'paid-report'], ['purchases-payable', 'payable-report']] as const) {
      service.list(kind, FILTERS, 1, 10).subscribe();
      http.expectOne((r) => r.url.endsWith(`/purchases/${path}/`)).flush({ count: 0, results: [], totals: { orders_count: 0, total: '0.00', balance: '0.00' } });
      service.export(kind, 'pdf', FILTERS).subscribe();
      http.expectOne((r) => r.url.endsWith(`/purchases/${path}/export/pdf/`)).flush(new Blob(['x']));
    }
  });
});
