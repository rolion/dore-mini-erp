import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { Supplier, SupplierApiError, SupplierDto } from '../models/supplier';
import {
  GENERIC_ERROR_MESSAGE,
  NETWORK_ERROR_MESSAGE,
  NOT_FOUND_MESSAGE,
  SuppliersApiService,
  VALIDATION_ERROR_MESSAGE,
} from './suppliers-api.service';

const DTO: SupplierDto = {
  id: 'abc',
  name: 'Distribuidora Sur',
  tax_id: 'NIT-1020',
  phone: '76543210',
  email: 'ventas@sur.com',
  notes: 'martes',
  active: true,
  created_at: '2026-10-29T10:00:00Z',
  updated_at: '2026-10-29T11:00:00Z',
};

const SUPPLIER: Supplier = {
  id: 'abc',
  name: 'Distribuidora Sur',
  taxId: 'NIT-1020',
  phone: '76543210',
  email: 'ventas@sur.com',
  notes: 'martes',
  active: true,
  createdAt: '2026-10-29T10:00:00Z',
  updatedAt: '2026-10-29T11:00:00Z',
};

const INPUT = { name: 'Distribuidora Sur', taxId: 'NIT-1020', phone: '', email: '', notes: '' };

describe('SuppliersApiService', () => {
  let service: SuppliersApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(SuppliersApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('lists with search, active, page and page_size and maps snake_case to camelCase (AC-10)', () => {
    let result: unknown;
    service.list({ search: 'sur', active: true, page: 2, pageSize: 10 }).subscribe((page) => (result = page));

    const req = http.expectOne((r) => r.url.endsWith('/suppliers/'));
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('search')).toBe('sur');
    expect(req.request.params.get('active')).toBe('true');
    expect(req.request.params.get('page')).toBe('2');
    expect(req.request.params.get('page_size')).toBe('10');
    req.flush({ count: 1, next: null, previous: null, results: [DTO] });

    expect(result).toEqual({ count: 1, next: null, previous: null, results: [SUPPLIER] });
  });

  it('omits empty search and undefined active (AC-10)', () => {
    service.list({ search: '' }).subscribe();
    const req = http.expectOne((r) => r.url.endsWith('/suppliers/'));
    expect(req.request.params.keys()).toEqual([]);
    req.flush({ count: 0, next: null, previous: null, results: [] });
  });

  it('creates sending tax_id in snake_case (AC-11)', () => {
    let created: Supplier | undefined;
    service.create(INPUT).subscribe((s) => (created = s));
    const req = http.expectOne((r) => r.url.endsWith('/suppliers/'));
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ name: 'Distribuidora Sur', tax_id: 'NIT-1020', phone: '', email: '', notes: '' });
    req.flush(DTO);
    expect(created).toEqual(SUPPLIER);
  });

  it('updates only the sent fields with PATCH (AC-11)', () => {
    service.update('abc', { taxId: '9' }).subscribe();
    const req = http.expectOne((r) => r.url.endsWith('/suppliers/abc/'));
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({ tax_id: '9' });
    req.flush(DTO);
  });

  it('gets, activates and deactivates (AC-10, AC-12)', () => {
    const results: Supplier[] = [];
    service.get('abc').subscribe((s) => results.push(s));
    http.expectOne((r) => r.url.endsWith('/suppliers/abc/') && r.method === 'GET').flush(DTO);
    service.activate('abc').subscribe((s) => results.push(s));
    http.expectOne((r) => r.url.endsWith('/suppliers/abc/activate/') && r.method === 'POST').flush(DTO);
    service.deactivate('abc').subscribe((s) => results.push(s));
    http.expectOne((r) => r.url.endsWith('/suppliers/abc/deactivate/') && r.method === 'POST').flush(DTO);
    expect(results).toEqual([SUPPLIER, SUPPLIER, SUPPLIER]);
  });

  it('maps 400 to field errors with the form field names (AC-11)', () => {
    let error: SupplierApiError | undefined;
    service.create(INPUT).subscribe({ error: (e: SupplierApiError) => (error = e) });
    http
      .expectOne((r) => r.url.endsWith('/suppliers/'))
      .flush({ name: ['El nombre es obligatorio.'], tax_id: ['Muy largo'], email: ['Ingresa un correo válido.'] }, {
        status: 400,
        statusText: 'Bad Request',
      });
    expect(error?.status).toBe(400);
    expect(error?.message).toBe(VALIDATION_ERROR_MESSAGE);
    expect(error?.fieldErrors).toEqual({
      name: ['El nombre es obligatorio.'],
      taxId: ['Muy largo'],
      email: ['Ingresa un correo válido.'],
    });
  });

  it('maps 404, network and other errors to friendly messages', () => {
    const cases: [number, string][] = [
      [404, NOT_FOUND_MESSAGE],
      [0, NETWORK_ERROR_MESSAGE],
      [500, GENERIC_ERROR_MESSAGE],
    ];
    for (const [status, message] of cases) {
      let error: SupplierApiError | undefined;
      service.get('abc').subscribe({ error: (e: SupplierApiError) => (error = e) });
      const req = http.expectOne((r) => r.url.endsWith('/suppliers/abc/'));
      if (status === 0) {
        req.error(new ProgressEvent('error'));
      } else {
        req.flush({}, { status, statusText: 'x' });
      }
      expect(error?.status).withContext(String(status)).toBe(status);
      expect(error?.message).toBe(message);
    }
  });
});
