import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { SettingsApiError } from '../models/setting';
import { SettingsApiService } from './settings-api.service';

describe('SettingsApiService', () => {
  let service: SettingsApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(SettingsApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('gets the settings of a module (API-01)', () => {
    let module = '';
    service.get('sales').subscribe((result) => (module = result.module));
    const req = http.expectOne((r) => r.url.endsWith('/settings/sales/'));
    expect(req.request.method).toBe('GET');
    req.flush({ module: 'sales', settings: [] });
    expect(module).toBe('sales');
  });

  it('saves a partial batch under the settings key (API-02)', () => {
    service.save('sales', { 'sales.max_discount_percent': '10' }).subscribe();
    const req = http.expectOne((r) => r.url.endsWith('/settings/sales/'));
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({ settings: { 'sales.max_discount_percent': '10' } });
    req.flush({ module: 'sales', settings: [] });
  });

  it('maps field errors of a 400 by setting key (AC-10)', () => {
    let error: SettingsApiError | undefined;
    service.save('sales', { 'sales.max_discount_percent': '200' }).subscribe({ error: (e: SettingsApiError) => (error = e) });
    http
      .expectOne((r) => r.url.endsWith('/settings/sales/'))
      .flush({ settings: { 'sales.max_discount_percent': ['Debe estar entre 0 y 100.'] } }, { status: 400, statusText: 'Bad Request' });
    expect(error?.status).toBe(400);
    expect(error?.fieldErrors).toEqual({ 'sales.max_discount_percent': 'Debe estar entre 0 y 100.' });
  });

  it('uses the detail of a 409 and a generic message on network failure (AC-11, EDGE-07)', () => {
    const errors: SettingsApiError[] = [];
    service.save('sales', { a: '1' }).subscribe({ error: (e: SettingsApiError) => errors.push(e) });
    http.expectOne((r) => r.url.endsWith('/settings/sales/')).flush({ detail: 'No habilitado.' }, { status: 409, statusText: 'Conflict' });
    service.get('sales').subscribe({ error: (e: SettingsApiError) => errors.push(e) });
    http.expectOne((r) => r.url.endsWith('/settings/sales/')).error(new ProgressEvent('error'));
    expect(errors[0].message).toBe('No habilitado.');
    expect(errors[1].status).toBe(0);
    expect(errors[1].message).toContain('No se pudo');
  });

  it('requests the history with filters and maps rows (API-03)', () => {
    let first = '';
    service.history('sales', { dateFrom: '2026-10-01', dateTo: '', setting: 'sales.max_discount_percent', page: 2 }).subscribe((page) => {
      first = `${page.count}:${page.results[0].changedBy}:${page.results[0].newValue}`;
    });
    const req = http.expectOne((r) => r.url.endsWith('/settings/sales/history/'));
    expect(req.request.params.get('date_from')).toBe('2026-10-01');
    expect(req.request.params.has('date_to')).toBeFalse();
    expect(req.request.params.get('setting')).toBe('sales.max_discount_percent');
    expect(req.request.params.get('page')).toBe('2');
    req.flush({
      count: 1,
      settings: [],
      results: [
        { id: '1', changed_at: '2026-10-27T10:00:00Z', changed_by: 'Ana', setting_key: 'k', setting_label: 'L', old_value: '1', new_value: '2' },
      ],
    });
    expect(first).toBe('1:Ana:2');
  });
});
