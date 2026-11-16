import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { AccountingApiError } from '../models/accounting';
import { AccountingApiService } from './accounting-api.service';

describe('AccountingApiService', () => {
  let service: AccountingApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(AccountingApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('maps accounts and filters by active', () => {
    let result: unknown;
    service.listAccounts(true).subscribe((r) => (result = r));
    const req = http.expectOne((r) => r.url.endsWith('/accounting/accounts/'));
    expect(req.request.params.get('active')).toBe('true');
    req.flush([{ id: 'a1', name: 'Caja', currency: 'BOB', is_active: true }]);
    expect(result).toEqual([{ id: 'a1', name: 'Caja', currency: 'BOB', kind: null, accountClass: null, code: null, isContra: false, hasEntries: false, openingBalance: '0.00', isActive: true }]);
  });

  it('configures a method with account_id and is_active', () => {
    let code = '';
    service.configureMethod('QR', 'a1', true).subscribe((m) => (code = m.code));
    const req = http.expectOne((r) => r.url.endsWith('/accounting/payment-methods/QR/'));
    expect(req.request.method).toBe('PUT');
    expect(req.request.body).toEqual({ account_id: 'a1', is_active: true });
    req.flush({ code: 'QR', label: 'QR', is_active: true, account: { id: 'a1', name: 'Banco', currency: 'BOB', is_active: true } });
    expect(code).toBe('QR');
  });

  it('exposes the 409 reason and blocking methods when deactivating an account in use', () => {
    let error: AccountingApiError | undefined;
    service.deactivateAccount('a1').subscribe({ error: (e: AccountingApiError) => (error = e) });
    http
      .expectOne((r) => r.url.endsWith('/accounting/accounts/a1/deactivate/'))
      .flush({ detail: 'No se puede desactivar.', code: 'account_in_use', methods: ['QR'] }, { status: 409, statusText: 'Conflict' });
    expect(error?.status).toBe(409);
    expect(error?.code).toBe('account_in_use');
    expect(error?.methods).toEqual(['QR']);
    expect(error?.message).toBe('No se puede desactivar.');
  });

  it('maps field errors of a 400', () => {
    let error: AccountingApiError | undefined;
    service.createAccount({ name: '', currency: 'BOB', kind: 'BANK' }).subscribe({ error: (e: AccountingApiError) => (error = e) });
    http.expectOne((r) => r.url.endsWith('/accounting/accounts/')).flush({ name: ['Ya existe.'] }, { status: 400, statusText: 'Bad Request' });
    expect(error?.fieldErrors['name']).toEqual(['Ya existe.']);
  });

  it('lists and toggles the accounting classifications', () => {
    let rows: unknown;
    service.listAccountClasses().subscribe((r) => (rows = r));
    http.expectOne((r) => r.url.endsWith('/accounting/account-classes/')).flush([{ code: 'ASSET', enabled: true }]);
    expect(rows).toEqual([{ code: 'ASSET', enabled: true }]);

    service.setAccountClassEnabled('COST', false).subscribe();
    const req = http.expectOne((r) => r.url.endsWith('/accounting/account-classes/COST/disable/'));
    expect(req.request.method).toBe('POST');
    req.flush({ code: 'COST', enabled: false });
    service.setAccountClassEnabled('COST', true).subscribe();
    http.expectOne((r) => r.url.endsWith('/accounting/account-classes/COST/enable/')).flush({ code: 'COST', enabled: true });
  });

  it('sends account_class and maps its field error', () => {
    let error: AccountingApiError | undefined;
    service.createAccount({ name: 'Costos', currency: 'BOB', kind: 'BANK', accountClass: 'COST' }).subscribe({ error: (e: AccountingApiError) => (error = e) });
    const req = http.expectOne((r) => r.url.endsWith('/accounting/accounts/'));
    expect(req.request.body).toEqual({ name: 'Costos', currency: 'BOB', kind: 'BANK', account_class: 'COST' });
    req.flush({ account_class: ['La clasificación contable está deshabilitada.'] }, { status: 400, statusText: 'Bad Request' });
    expect(error?.fieldErrors['accountClass']).toEqual(['La clasificación contable está deshabilitada.']);
  });

  it('filters accounts by classification and sends code and contra flag', () => {
    service.listAccounts(undefined, 'ASSET').subscribe();
    const list = http.expectOne((r) => r.url.endsWith('/accounting/accounts/'));
    expect(list.request.params.get('account_class')).toBe('ASSET');
    list.flush([]);
    let created: unknown;
    service.createAccount({ name: 'Depreciación', currency: 'BOB', code: '121005', accountClass: 'ASSET', isContra: true }).subscribe((a) => (created = a));
    const req = http.expectOne((r) => r.url.endsWith('/accounting/accounts/') && r.method === 'POST');
    expect(req.request.body).toEqual({ name: 'Depreciación', currency: 'BOB', code: '121005', account_class: 'ASSET', is_contra: true });
    req.flush({ id: 'a1', name: 'Depreciación', currency: 'BOB', code: '121005', account_class: 'ASSET', is_contra: true, has_entries: true, is_active: true });
    expect((created as { hasEntries: boolean }).hasEntries).toBeTrue();
  });
});
