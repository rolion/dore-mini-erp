import { provideTestTranslations } from '../../../core/i18n/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ExpensesApiError, GENERIC_ERROR_MESSAGE, NETWORK_ERROR_MESSAGE } from '../models/api-error';
import { ExpenseDto, ExpenseInput } from '../models/expense';
import { ExpensePage, ExpensesApiService } from './expenses-api.service';

const DTO: ExpenseDto = {
  id: 'e1',
  description: 'Harina',
  amount: '120.50',
  expense_date: '2026-10-05',
  category: { id: 'c1', name: 'Materia prima', active: true },
  payment_method: 'QR',
  supplier_name: 'Molino',
  notes: 'n',
  status: 'ACTIVE',
  voided_at: null,
  created_at: '2026-10-05T10:00:00Z',
  updated_at: '2026-10-05T10:00:00Z',
};

const INPUT: ExpenseInput = {
  description: 'Harina',
  amount: '120.50',
  categoryId: 'c1',
  expenseDate: '2026-10-05',
  paymentMethod: 'QR',
  supplierName: 'Molino',
  notes: 'n',
};

describe('ExpensesApiService', () => {
  let service: ExpensesApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(ExpensesApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('lists with filters as query params and maps the page and the filter total (AC-08)', () => {
    let result: ExpensePage | undefined;
    service
      .list({ dateFrom: '2026-10-01', dateTo: '2026-10-31', categoryId: 'c1', status: 'all', page: 2, pageSize: 10 })
      .subscribe((page) => (result = page));

    const req = http.expectOne((r) => r.url === '/api/expenses/');
    expect(req.request.params.get('date_from')).toBe('2026-10-01');
    expect(req.request.params.get('date_to')).toBe('2026-10-31');
    expect(req.request.params.get('category_id')).toBe('c1');
    expect(req.request.params.get('status')).toBe('all');
    expect(req.request.params.get('page')).toBe('2');
    expect(req.request.params.get('page_size')).toBe('10');
    req.flush({ count: 1, next: null, previous: null, results: [DTO], total_amount: '120.50' });

    expect(result?.totalAmount).toBe('120.50');
    expect(result?.results[0].expenseDate).toBe('2026-10-05');
    expect(result?.results[0].paymentMethod).toBe('QR');
  });

  it('omits empty filters', () => {
    service.list().subscribe();
    const req = http.expectOne('/api/expenses/');
    expect(req.request.params.keys()).toEqual([]);
    req.flush({ count: 0, next: null, previous: null, results: [], total_amount: '0.00' });
  });

  it('creates with snake_case fields and returns the camelCase expense (AC-03)', () => {
    let created = '';
    service.create(INPUT).subscribe((expense) => (created = expense.category.name));
    const req = http.expectOne('/api/expenses/');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({
      description: 'Harina',
      amount: '120.50',
      category_id: 'c1',
      expense_date: '2026-10-05',
      payment_method: 'QR',
      supplier_name: 'Molino',
      notes: 'n',
    });
    req.flush(DTO);
    expect(created).toBe('Materia prima');
  });

  it('patches only the given fields (AC-06)', () => {
    service.update('e1', { amount: '75.00' }).subscribe();
    const req = http.expectOne('/api/expenses/e1/');
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({ amount: '75.00' });
    req.flush(DTO);
  });

  it('voids with a POST to the void action (AC-07)', () => {
    service.void('e1').subscribe();
    const req = http.expectOne('/api/expenses/e1/void/');
    expect(req.request.method).toBe('POST');
    req.flush({ ...DTO, status: 'VOIDED', voided_at: '2026-10-06T10:00:00Z' });
  });

  it('sends the chosen accounts and the idempotency key, and maps the posted expense (GAS-01, API-01, API-03)', () => {
    let posted: boolean | undefined;
    service
      .create({ ...INPUT, expenseAccountId: 'a1', paymentAccountId: 'a2', idempotencyKey: 'k1' })
      .subscribe((expense) => (posted = expense.posted && expense.journalEntryId === 'j1' && expense.expenseAccount?.name === 'Alquiler'));
    const req = http.expectOne('/api/expenses/');
    expect(req.request.body).toEqual(jasmine.objectContaining({ expense_account_id: 'a1', payment_account_id: 'a2', idempotency_key: 'k1' }));
    req.flush({ ...DTO, posted: true, journal_entry_id: 'j1', expense_account: { id: 'a1', code: '5', name: 'Alquiler', active: true } });
    expect(posted).toBeTrue();
  });

  it('asks for the posting options with date, method and category (GAS-01, API-02)', () => {
    let covered: boolean | undefined;
    service.postingOptions('2026-10-05', 'c1', 'CASH').subscribe((o) => (covered = o.covered && o.paymentAccounts.length === 1));
    const req = http.expectOne((r) => r.url === '/api/expenses/posting-options/');
    expect(req.request.params.get('expense_date')).toBe('2026-10-05');
    expect(req.request.params.get('category_id')).toBe('c1');
    expect(req.request.params.get('payment_method')).toBe('CASH');
    req.flush({ covered: true, reason: null, expense_account: null, payment_account: null, issues: [], expense_accounts: [], payment_accounts: [{ id: 'a', code: null, name: 'Caja', active: true }] });
    expect(covered).toBeTrue();
  });

  it('keeps the code and the missing-configuration issues of a posting error and its account fields (GAS-01)', () => {
    let received: ExpensesApiError | undefined;
    service.create(INPUT).subscribe({ error: (e: ExpensesApiError) => (received = e) });
    http.expectOne('/api/expenses/').flush(
      { code: 'posting_configuration_missing', detail: 'Falta', issues: [{ code: 'category_unconfigured' }], expense_account_id: ['Cuenta inválida.'] },
      { status: 400, statusText: 'Bad Request' },
    );
    expect(received?.code).toBe('posting_configuration_missing');
    expect(received?.issues.length).toBe(1);
    expect(received?.fieldErrors['expenseAccountId']).toEqual(['Cuenta inválida.']);
  });

  it('turns 400 into field errors with form field names (AC-04)', () => {
    let error: ExpensesApiError | null = null;
    service.create(INPUT).subscribe({ error: (err: ExpensesApiError) => (error = err) });
    http
      .expectOne('/api/expenses/')
      .flush({ amount: ['El monto debe ser mayor a cero.'], category_id: ['La categoría no existe.'] }, { status: 400, statusText: 'Bad Request' });
    const received = error as unknown as ExpensesApiError;
    expect(received.status).toBe(400);
    expect(received.fieldErrors['amount']).toEqual(['El monto debe ser mayor a cero.']);
    expect(received.fieldErrors['categoryId']).toEqual(['La categoría no existe.']);
  });

  it('keeps the stable code and message of a 409 (AC-07)', () => {
    let error: ExpensesApiError | null = null;
    service.void('e1').subscribe({ error: (err: ExpensesApiError) => (error = err) });
    http
      .expectOne('/api/expenses/e1/void/')
      .flush({ code: 'already_voided', detail: 'El gasto ya está anulado.' }, { status: 409, statusText: 'Conflict' });
    const received = error as unknown as ExpensesApiError;
    expect([received.status, received.code, received.message]).toEqual([409, 'already_voided', 'El gasto ya está anulado.']);
  });

  it('maps network and unexpected errors to friendly messages', () => {
    const messages: string[] = [];
    service.get('e1').subscribe({ error: (err: ExpensesApiError) => messages.push(err.message) });
    http.expectOne('/api/expenses/e1/').error(new ProgressEvent('error'));
    service.get('e2').subscribe({ error: (err: ExpensesApiError) => messages.push(err.message) });
    http.expectOne('/api/expenses/e2/').flush('boom', { status: 500, statusText: 'Server Error' });
    expect(messages).toEqual([NETWORK_ERROR_MESSAGE(), GENERIC_ERROR_MESSAGE()]);
  });
});
