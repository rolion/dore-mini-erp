import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { AccountingApiError } from '../models/accounting';
import { PostingConfigApiService } from './posting-config-api.service';

const account = { id: 'a1', code: '410001', name: 'Ingresos', is_active: true };

describe('PostingConfigApiService', () => {
  let service: PostingConfigApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(PostingConfigApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('reads the module configuration and maps it to camelCase (AC-01)', () => {
    let result: unknown;
    service.get('sales').subscribe((r) => (result = r));
    const request = http.expectOne((r) => r.url.endsWith('/accounting/posting-config/') && r.params.get('module') === 'sales');
    request.flush({
      module: 'sales',
      module_label: 'Ventas',
      accounting_enabled: true,
      ready: false,
      events: [{ code: 'SALE_RECOGNITION', label: 'x', issues: [], preview: [{ side: 'CREDIT', role: 'SALES_INCOME', label: 'Ingresos', account, status: 'ok' }] }],
      roles: [{ role: 'SALES_INCOME', label: 'Ingresos', account_class: 'INCOME', account, issue: null, shared_with: [] }],
      methods: [{ code: 'CASH', label: 'Efectivo', is_active: true, account: null, issue: 'falta' }],
      categories: [{ category_id: 'c1', account, issue: null }],
    });
    expect(result).toEqual({
      module: 'sales',
      moduleLabel: 'Ventas',
      accountingEnabled: true,
      ready: false,
      events: [{ code: 'SALE_RECOGNITION', label: 'x', issues: [], preview: [{ side: 'CREDIT', role: 'SALES_INCOME', label: 'Ingresos', account: { id: 'a1', code: '410001', name: 'Ingresos', isActive: true }, status: 'ok' }] }],
      roles: [{ role: 'SALES_INCOME', label: 'Ingresos', accountClass: 'INCOME', account: { id: 'a1', code: '410001', name: 'Ingresos', isActive: true }, issue: null, sharedWith: [] }],
      methods: [{ code: 'CASH', label: 'Efectivo', isActive: true, account: null, issue: 'falta' }],
      categories: [{ categoryId: 'c1', account: { id: 'a1', code: '410001', name: 'Ingresos', isActive: true }, issue: null }],
    });
  });

  it('sends the account id (or null to clear) for roles and categories (AC-02)', () => {
    service.setRoleAccount('SALES_INCOME', 'a1').subscribe();
    const role = http.expectOne((r) => r.method === 'PUT' && r.url.endsWith('/posting-config/roles/SALES_INCOME/'));
    expect(role.request.body).toEqual({ account_id: 'a1' });
    role.flush({ role: 'SALES_INCOME', label: 'x', account_class: 'INCOME', account, issue: null, shared_with: [] });
    service.setCategoryAccount('c1', null).subscribe();
    const category = http.expectOne((r) => r.method === 'PUT' && r.url.endsWith('/posting-config/categories/c1/'));
    expect(category.request.body).toEqual({ account_id: null });
    category.flush({ category_id: 'c1', account: null, issue: null });
  });

  it('turns a 400 into a field error and a 404 into a message (AC-03)', () => {
    let error: AccountingApiError | undefined;
    service.setRoleAccount('SALES_INCOME', 'x').subscribe({ error: (e: AccountingApiError) => (error = e) });
    http.expectOne((r) => r.method === 'PUT').flush({ account_id: ['La cuenta no existe en esta empresa.'] }, { status: 400, statusText: 'Bad Request' });
    expect(error?.status).toBe(400);
    expect(error?.fieldErrors['accountId']).toEqual(['La cuenta no existe en esta empresa.']);
    service.get('sales').subscribe({ error: (e: AccountingApiError) => (error = e) });
    http.expectOne((r) => r.method === 'GET').flush({ detail: 'No existe.' }, { status: 404, statusText: 'Not Found' });
    expect(error?.status).toBe(404);
  });
});
