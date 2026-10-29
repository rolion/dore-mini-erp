import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { PurchaseApiError, PurchaseDto, PurchaseSummaryDto } from '../models/purchase';
import { makePurchase } from '../testing/purchase-fixtures';
import {
  GENERIC_ERROR_MESSAGE,
  NETWORK_ERROR_MESSAGE,
  NOT_EDITABLE_MESSAGE,
  NOT_FOUND_MESSAGE,
  PurchasesApiService,
  VALIDATION_ERROR_MESSAGE,
  toFieldErrors,
} from './purchases-api.service';

const DTO: PurchaseDto = {
  id: 'c-1',
  supplier: { id: 's-1', name: 'Distribuidora Sur', active: true },
  purchase_date: '2026-10-29',
  external_reference: 'F-100',
  notes: 'Entrega el martes',
  status: 'draft',
  currency: 'BOB',
  editable: true,
  items: [
    {
      id: 'i-1',
      product_id: 'p-1',
      product_name: 'Harina',
      unit_abbreviation: 'kg',
      quantity: '2.500',
      unit_price: '10.00',
      subtotal: '25.00',
    },
  ],
  total: '25.00',
  created_at: '2026-10-29T10:00:00Z',
  updated_at: '2026-10-29T11:00:00Z',
};

const INPUT = {
  supplierId: 's-1',
  purchaseDate: '2026-10-29',
  externalReference: 'F-100',
  notes: '',
  items: [{ productId: 'p-1', quantity: '2.5', unitPrice: '10.00' }],
};

describe('PurchasesApiService', () => {
  let service: PurchasesApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(PurchasesApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('lists purchases with the supplier filter and paging, mapping the rows', () => {
    const row: PurchaseSummaryDto = {
      id: 'c-1',
      purchase_date: '2026-10-29',
      supplier: { id: 's-1', name: 'Sur' },
      external_reference: '',
      total: '25.00',
      currency: 'BOB',
      status: 'draft',
      items_count: 2,
    };
    let count = -1;
    let first = '';
    service.list({ supplierId: 's-1', page: 2, pageSize: 10 }).subscribe((page) => {
      count = page.count;
      first = `${page.results[0].supplier.name}/${page.results[0].itemsCount}/${page.results[0].purchaseDate}`;
    });
    const req = http.expectOne((r) => r.url.endsWith('/purchases/'));
    expect(req.request.params.get('supplier_id')).toBe('s-1');
    expect(req.request.params.get('page')).toBe('2');
    expect(req.request.params.get('page_size')).toBe('10');
    req.flush({ count: 1, next: null, previous: null, results: [row] });
    expect(count).toBe(1);
    expect(first).toBe('Sur/2/2026-10-29');
  });

  it('maps the detail from snake_case', () => {
    let result = makePurchase();
    service.get('c-1').subscribe((purchase) => (result = purchase));
    http.expectOne((r) => r.url.endsWith('/purchases/c-1/')).flush(DTO);
    expect(result).toEqual(makePurchase());
  });

  it('sends amounts as text and never sends a total (AC-05)', () => {
    service.create(INPUT).subscribe();
    const req = http.expectOne((r) => r.url.endsWith('/purchases/'));
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({
      supplier_id: 's-1',
      purchase_date: '2026-10-29',
      external_reference: 'F-100',
      notes: '',
      items: [{ product_id: 'p-1', quantity: '2.5', unit_price: '10.00' }],
    });
    req.flush(DTO);
  });

  it('patches only what it is given', () => {
    service.update('c-1', { notes: 'x' }).subscribe();
    const req = http.expectOne((r) => r.url.endsWith('/purchases/c-1/'));
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({ notes: 'x' });
    req.flush(DTO);
  });

  it('maps header and per-line validation errors (AC-03)', () => {
    let error: PurchaseApiError | undefined;
    service.create(INPUT).subscribe({ error: (e: PurchaseApiError) => (error = e) });
    http.expectOne((r) => r.url.endsWith('/purchases/')).flush(
      {
        supplier_id: ['Selecciona un proveedor activo.'],
        items: [{}, { quantity: ['La cantidad debe ser mayor a cero.'], unit_price: ['No negativo.'] }],
      },
      { status: 400, statusText: 'Bad Request' },
    );
    expect(error?.status).toBe(400);
    expect(error?.message).toBe(VALIDATION_ERROR_MESSAGE);
    expect(error?.fieldErrors.header.supplierId).toBe('Selecciona un proveedor activo.');
    expect(error?.fieldErrors.items).toEqual([{}, { quantity: 'La cantidad debe ser mayor a cero.', unitPrice: 'No negativo.' }]);
  });

  it('reads a general message of items (too many lines)', () => {
    const errors = toFieldErrors({ items: ['Una compra admite como máximo 200 líneas.'] });
    expect(errors.items).toEqual([]);
    expect(errors.itemsMessage).toBe('Una compra admite como máximo 200 líneas.');
  });

  it('maps network, 404, 409 and unexpected errors', () => {
    const cases: [number, string][] = [
      [0, NETWORK_ERROR_MESSAGE],
      [404, NOT_FOUND_MESSAGE],
      [409, NOT_EDITABLE_MESSAGE],
      [500, GENERIC_ERROR_MESSAGE],
    ];
    for (const [status, message] of cases) {
      let error: PurchaseApiError | undefined;
      service.get('c-1').subscribe({ error: (e: PurchaseApiError) => (error = e) });
      const req = http.expectOne((r) => r.url.endsWith('/purchases/c-1/'));
      if (status === 0) {
        req.error(new ProgressEvent('error'));
      } else {
        req.flush({}, { status, statusText: 'x' });
      }
      expect(error?.message).withContext(String(status)).toBe(message);
      expect(error?.status).toBe(status);
    }
  });
});
