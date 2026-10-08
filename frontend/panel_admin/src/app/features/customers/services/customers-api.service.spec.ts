import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { Customer, CustomerApiError, CustomerDto, DuplicateCustomerError } from '../models/customer';
import {
  CustomersApiService,
  DUPLICATE_PHONE_MESSAGE,
  GENERIC_ERROR_MESSAGE,
  NETWORK_ERROR_MESSAGE,
  NOT_FOUND_MESSAGE,
} from './customers-api.service';

const DTO: CustomerDto = {
  id: 'abc',
  name: 'Ana Pérez',
  phone: '+59176543210',
  email: 'ana@example.com',
  notes: 'vip',
  active: true,
  created_at: '2026-10-08T10:00:00Z',
  updated_at: '2026-10-08T11:00:00Z',
};

const CUSTOMER: Customer = {
  id: 'abc',
  name: 'Ana Pérez',
  phone: '+59176543210',
  email: 'ana@example.com',
  notes: 'vip',
  active: true,
  createdAt: '2026-10-08T10:00:00Z',
  updatedAt: '2026-10-08T11:00:00Z',
};

const INPUT = { name: 'Ana Pérez', phone: '7654 3210', email: '', notes: '' };

describe('CustomersApiService', () => {
  let service: CustomersApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(CustomersApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  /** Se suscribe ya (lo que dispara la petición) y entrega el error cuando llega la respuesta simulada. */
  function watchError(source: { subscribe: (o: { error: (e: unknown) => void }) => unknown }): { error: CustomerApiError } {
    const holder = { error: undefined as unknown as CustomerApiError };
    source.subscribe({ error: (e) => (holder.error = e as CustomerApiError) });
    return holder;
  }

  it('lists customers sending search, active, page and page_size and maps the DTOs (AC-06, AC-10)', () => {
    let result: unknown;
    service.list({ search: '765', active: true, page: 2, pageSize: 10 }).subscribe((p) => (result = p));

    const req = http.expectOne((r) => r.url === '/api/customers/');
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('search')).toBe('765');
    expect(req.request.params.get('active')).toBe('true');
    expect(req.request.params.get('page')).toBe('2');
    expect(req.request.params.get('page_size')).toBe('10');
    req.flush({ count: 1, next: null, previous: null, results: [DTO] });

    expect(result).toEqual({ count: 1, next: null, previous: null, results: [CUSTOMER] });
  });

  it('omits empty filters when listing (AC-10)', () => {
    service.list({ search: '', active: undefined }).subscribe();
    const req = http.expectOne('/api/customers/');
    expect(req.request.params.keys()).toEqual([]);
    req.flush({ count: 0, next: null, previous: null, results: [] });
  });

  it('gets a customer by id (AC-13)', () => {
    let result: unknown;
    service.get('abc').subscribe((c) => (result = c));
    const req = http.expectOne('/api/customers/abc/');
    expect(req.request.method).toBe('GET');
    req.flush(DTO);
    expect(result).toEqual(CUSTOMER);
  });

  it('creates a customer without confirm_duplicate by default (AC-11)', () => {
    service.create(INPUT).subscribe();
    const req = http.expectOne('/api/customers/');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual(INPUT);
    req.flush(DTO);
  });

  it('sends confirm_duplicate when the duplicate is confirmed (AC-12)', () => {
    service.create(INPUT, true).subscribe();
    const req = http.expectOne('/api/customers/');
    expect(req.request.body).toEqual({ ...INPUT, confirm_duplicate: true });
    req.flush(DTO);
  });

  it('maps a 409 duplicate_phone to DuplicateCustomerError with the matches (AC-12)', () => {
    const matches = [{ id: 'x', name: 'Otra', phone: '+59176543210', active: false }];
    const holder = watchError(service.create(INPUT));
    http
      .expectOne('/api/customers/')
      .flush({ code: 'duplicate_phone', detail: 'dup', matches }, { status: 409, statusText: 'Conflict' });

    expect(holder.error instanceof DuplicateCustomerError).toBeTrue();
    expect((holder.error as DuplicateCustomerError).matches).toEqual(matches);
    expect(holder.error.message).toBe(DUPLICATE_PHONE_MESSAGE);
    expect(holder.error.status).toBe(409);
  });

  it('treats a 409 without the duplicate code as a generic error (AC-12)', () => {
    const holder = watchError(service.create(INPUT));
    http.expectOne('/api/customers/').flush({ detail: 'otro' }, { status: 409, statusText: 'Conflict' });
    expect(holder.error instanceof DuplicateCustomerError).toBeFalse();
    expect(holder.error.message).toBe(GENERIC_ERROR_MESSAGE);
  });

  it('updates with PATCH sending only the given fields (AC-11)', () => {
    service.update('abc', { name: 'Beatriz', notes: 'x' }).subscribe();
    const req = http.expectOne('/api/customers/abc/');
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({ name: 'Beatriz', notes: 'x' });
    req.flush(DTO);
  });

  it('activates and deactivates with POST (AC-10, AC-13)', () => {
    service.deactivate('abc').subscribe();
    const off = http.expectOne('/api/customers/abc/deactivate/');
    expect(off.request.method).toBe('POST');
    off.flush({ ...DTO, active: false });

    service.activate('abc').subscribe();
    const on = http.expectOne('/api/customers/abc/activate/');
    expect(on.request.method).toBe('POST');
    on.flush(DTO);
  });

  it('maps 400 to field errors using the form field names (AC-11)', () => {
    const holder = watchError(service.create(INPUT));
    http
      .expectOne('/api/customers/')
      .flush({ name: ['El nombre es obligatorio.'], email: ['Ingresa un correo válido.'], x: ['ignorado'] },
        { status: 400, statusText: 'Bad Request' });

    expect(holder.error.status).toBe(400);
    expect(holder.error.fieldErrors).toEqual({
      name: ['El nombre es obligatorio.'],
      email: ['Ingresa un correo válido.'],
    });
  });

  it('maps 404, network and other errors to friendly messages (AC-13)', () => {
    const notFound = watchError(service.get('x'));
    http.expectOne('/api/customers/x/').flush({ detail: 'no' }, { status: 404, statusText: 'Not Found' });
    expect(notFound.error.message).toBe(NOT_FOUND_MESSAGE);

    const network = watchError(service.get('y'));
    http.expectOne('/api/customers/y/').error(new ProgressEvent('error'));
    expect(network.error.message).toBe(NETWORK_ERROR_MESSAGE);
    expect(network.error.status).toBe(0);

    const generic = watchError(service.get('z'));
    http.expectOne('/api/customers/z/').flush('', { status: 500, statusText: 'Server Error' });
    expect(generic.error.message).toBe(GENERIC_ERROR_MESSAGE);
  });
});
