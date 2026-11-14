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
    expect(result).toEqual([{ id: 'a1', name: 'Caja', currency: 'BOB', isActive: true }]);
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
    service.createAccount({ name: '', currency: 'BOB' }).subscribe({ error: (e: AccountingApiError) => (error = e) });
    http.expectOne((r) => r.url.endsWith('/accounting/accounts/')).flush({ name: ['Ya existe.'] }, { status: 400, statusText: 'Bad Request' });
    expect(error?.fieldErrors['name']).toEqual(['Ya existe.']);
  });
});
