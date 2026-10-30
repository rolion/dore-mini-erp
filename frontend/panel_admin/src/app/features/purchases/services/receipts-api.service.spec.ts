import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { Page } from '../../../shared/models/page';
import { Receipt, ReceiptApiError, ReceiptSummary, ReceptionForm } from '../models/receipt';
import { ReceiptsApiService, toReceiptFieldErrors } from './receipts-api.service';

const RECEIPT_DTO = {
  id: 'r-1',
  reference: 'REC-1A2B3C4D',
  purchase: { id: 'c-1', reference: 'COM-1A2B3C4D' },
  receipt_date: '2026-10-30',
  status: 'confirmed',
  user_name: 'ana',
  created_at: '2026-10-30T12:00:00Z',
  warehouse: { id: 'w-1', name: 'Central' },
  lines: [{ item_id: 'i-1', product: { id: 'p-1', name: 'Harina' }, unit: { abbreviation: 'kg' }, quantity: '4.000' }],
  movements: [
    { id: 'm-1', product: { id: 'p-1', name: 'Harina' }, warehouse: { id: 'w-1', name: 'Central' }, quantity: '4.000', unit: { abbreviation: 'kg' } },
  ],
};

describe('ReceiptsApiService', () => {
  let service: ReceiptsApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(ReceiptsApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('maps the reception form (AC-14)', () => {
    let form: ReceptionForm | undefined;
    service.receptionForm('c-1').subscribe((result) => (form = result));
    http.expectOne((r) => r.url.endsWith('/purchases/c-1/reception-form/')).flush({
      inventory_enabled: true,
      warehouses: [{ id: 'w-1', name: 'Central', is_default: true }],
      warehouse_id: 'w-1',
      lines: [
        {
          item_id: 'i-1', product: { id: 'p-1', name: 'Harina' }, unit: { abbreviation: 'kg' },
          allows_fractions: true, tracks_stock: true, ordered: '10.000', received: '4.000', pending: '6.000',
        },
      ],
    });
    expect(form?.inventoryEnabled).toBeTrue();
    expect(form?.warehouses).toEqual([{ id: 'w-1', name: 'Central', isDefault: true }]);
    expect(form?.lines[0]).toEqual(jasmine.objectContaining({ itemId: 'i-1', tracksStock: true, pending: '6.000', unitAbbreviation: 'kg' }));
  });

  it('lists the receipts of a purchase (AC-13)', () => {
    let page: Page<ReceiptSummary> | undefined;
    service.list('c-1').subscribe((result) => (page = result));
    http.expectOne((r) => r.url.endsWith('/purchases/c-1/receipts/')).flush({
      count: 1, next: null, previous: null,
      results: [{ id: 'r-1', reference: 'REC-1', receipt_date: '2026-10-30', status: 'confirmed', user_name: 'ana', lines_count: 2 }],
    });
    expect(page?.results[0]).toEqual({ id: 'r-1', reference: 'REC-1', receiptDate: '2026-10-30', status: 'confirmed', userName: 'ana', linesCount: 2 });
  });

  it('maps the detail with warehouse and movements, and keeps null movements (AC-13, AC-24)', () => {
    let receipt: Receipt | undefined;
    service.get('c-1', 'r-1').subscribe((result) => (receipt = result));
    http.expectOne((r) => r.url.endsWith('/purchases/c-1/receipts/r-1/')).flush(RECEIPT_DTO);
    expect(receipt?.warehouse).toEqual({ id: 'w-1', name: 'Central' });
    expect(receipt?.lines[0].productName).toBe('Harina');
    expect(receipt?.movements?.[0]).toEqual({ id: 'm-1', reference: '', productName: 'Harina', warehouseName: 'Central', quantity: '4.000', unitAbbreviation: 'kg', status: 'confirmed', reversedBy: null });
    expect(receipt?.inventoryMode).toBeNull();
    expect(receipt?.lines[0].stockEntry).toBeNull();
    service.get('c-1', 'r-1').subscribe((result) => (receipt = result));
    http.expectOne((r) => r.url.endsWith('/receipts/r-1/')).flush({ ...RECEIPT_DTO, warehouse: null, movements: null });
    expect(receipt?.movements).toBeNull();
  });

  it('creates with the idempotency id, omitting the warehouse when there is none (AC-22)', () => {
    service.create('c-1', { receiptId: 'x-1', receiptDate: '2026-10-30', warehouseId: null, lines: [{ itemId: 'i-1', quantity: '4.000' }] }).subscribe();
    const req = http.expectOne((r) => r.url.endsWith('/purchases/c-1/receipts/'));
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ receipt_id: 'x-1', receipt_date: '2026-10-30', lines: [{ item_id: 'i-1', quantity: '4.000' }] });
    req.flush(RECEIPT_DTO);
    service.create('c-1', { receiptId: 'x-2', receiptDate: '2026-10-30', warehouseId: 'w-1', lines: [] }).subscribe();
    const second = http.expectOne((r) => r.url.endsWith('/purchases/c-1/receipts/'));
    expect(second.request.body['warehouse_id']).toBe('w-1');
    second.flush(RECEIPT_DTO);
  });

  it('turns a 400 into field and line errors', () => {
    const errors = toReceiptFieldErrors({ receipt_date: ['Futura.'], warehouse_id: ['Falta.'], lines: [{}, { quantity: ['Excede.'] }] });
    expect(errors.receiptDate).toBe('Futura.');
    expect(errors.warehouseId).toBe('Falta.');
    expect(errors.linesMessage).toBeUndefined();
    expect(errors.lines[0].quantity).toBeUndefined();
    expect(errors.lines[1].quantity).toBe('Excede.');
    expect(toReceiptFieldErrors({ lines: ['Indica al menos un producto recibido.'] }).linesMessage).toContain('al menos un producto');
    expect(toReceiptFieldErrors(null)).toEqual({ lines: [] });
  });

  it('maps the HTTP errors to readable messages', () => {
    const results: ReceiptApiError[] = [];
    for (const [status, body] of [[0, null], [404, {}], [409, { detail: 'Solo una compra confirmada admite recepciones.' }], [500, {}]] as const) {
      service.create('c-1', { receiptId: 'x', receiptDate: '2026-10-30', warehouseId: null, lines: [] }).subscribe({ error: (err: ReceiptApiError) => results.push(err) });
      http.expectOne((r) => r.url.endsWith('/receipts/')).flush(body, { status, statusText: 'x' });
    }
    expect(results.map((e) => e.status)).toEqual([0, 404, 409, 500]);
    expect(results[2].message).toBe('Solo una compra confirmada admite recepciones.');
    service.create('c-1', { receiptId: 'x', receiptDate: '2026-10-30', warehouseId: null, lines: [] }).subscribe({ error: (err: ReceiptApiError) => results.push(err) });
    http.expectOne((r) => r.url.endsWith('/receipts/')).flush({ lines: [{ quantity: ['No puede superar el pendiente (1.000).'] }] }, { status: 400, statusText: 'x' });
    expect(results[4].fieldErrors.lines[0].quantity).toContain('pendiente');
  });

  it('posts the reason to revert a receipt and maps the reversal data (API-03, API-04)', () => {
    let receipt: Receipt | undefined;
    service.revert('c-1', 'r-1', 'Error de conteo').subscribe((result) => (receipt = result));
    const req = http.expectOne((r) => r.url.endsWith('/purchases/c-1/receipts/r-1/revert/'));
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ reason: 'Error de conteo' });
    req.flush({
      ...RECEIPT_DTO,
      status: 'reverted',
      can_revert: false,
      reversal: { reverted_at: '2026-10-31T10:00:00Z', user_name: 'ana', reason: 'Error de conteo' },
      movements: [{ ...RECEIPT_DTO.movements[0], status: 'reversed', reversed_by: { id: 'm-2', reference: 'REC-1' } }],
    });
    expect(receipt?.status).toBe('reverted');
    expect(receipt?.canRevert).toBeFalse();
    expect(receipt?.reversal).toEqual({ revertedAt: '2026-10-31T10:00:00Z', userName: 'ana', reason: 'Error de conteo' });
    expect(receipt?.movements?.[0].status).toBe('reversed');
    expect(receipt?.movements?.[0].reversedBy).toEqual({ id: 'm-2', reference: 'REC-1' });
  });

  it('defaults the new fields for responses without reversal data', () => {
    let receipt: Receipt | undefined;
    service.get('c-1', 'r-1').subscribe((result) => (receipt = result));
    http.expectOne((r) => r.url.endsWith('/purchases/c-1/receipts/r-1/')).flush(RECEIPT_DTO);
    expect(receipt?.canRevert).toBeFalse();
    expect(receipt?.reversal).toBeNull();
    expect(receipt?.movements?.[0].status).toBe('confirmed');
  });

  it('maps the reversal errors: reason (400), insufficient stock with every line and other conflicts (409)', () => {
    const errors: ReceiptApiError[] = [];
    const revert = (body: object, status: number): void => {
      service.revert('c-1', 'r-1', 'x').subscribe({ error: (err: ReceiptApiError) => errors.push(err) });
      http.expectOne((r) => r.url.endsWith('/revert/')).flush(body, { status, statusText: 'x' });
    };
    revert({ reason: ['El motivo es obligatorio.'] }, 400);
    revert({
      code: 'insufficient_stock', detail: 'No hay saldo.', warehouse: { id: 'w', name: 'Central' },
      lines: [
        { product: { id: 'p-1', name: 'Harina' }, unit: { abbreviation: 'kg' }, requested: '10.000', available: '2.000' },
        { product: { id: 'p-2', name: 'Azúcar' }, unit: { abbreviation: 'kg' }, requested: '5.000', available: '0.000' },
      ],
    }, 409);
    revert({ code: 'already_reverted', detail: 'La recepción ya fue revertida.' }, 409);
    expect(errors[0].fieldErrors.reason).toBe('El motivo es obligatorio.');
    expect(errors[1].code).toBe('insufficient_stock');
    expect(errors[1].shortage?.warehouseName).toBe('Central');
    expect(errors[1].shortage?.lines.map((l) => [l.productName, l.available])).toEqual([['Harina', '2.000'], ['Azúcar', '0.000']]);
    expect(errors[2].code).toBe('already_reverted');
    expect(errors[2].shortage).toBeNull();
    expect(errors[2].message).toBe('La recepción ya fue revertida.');
  });
});
