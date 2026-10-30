import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Adoption, lineValueMessage, lineValueState, previewUnitCost } from '../models/valuation';
import { ValuationApiError, ValuationApiService } from './valuation-api.service';

const ADOPTION_DTO = {
  status: 'adopted',
  adoption: {
    id: 'a-1',
    cutoff_at: '2026-10-30T12:00:00Z',
    method: 'weighted_moving_average',
    user_name: 'ana',
    lines: [
      {
        product_id: 'p-1',
        product_name: 'Harina',
        unit_abbreviation: 'kg',
        reconciled_quantity: '3.0000',
        total_value: '10.00',
        unit_cost: '3.333333',
        declared_zero: false,
        source: 'Ingreso manual',
      },
    ],
  },
};

describe('ValuationApiService', () => {
  let http: HttpTestingController;
  let service: ValuationApiService;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    http = TestBed.inject(HttpTestingController);
    service = TestBed.inject(ValuationApiService);
  });

  afterEach(() => http.verify());

  it('reads the valuation and maps the adoption (AC-10)', () => {
    let result: unknown;
    service.get().subscribe((v) => (result = v));
    http.expectOne('/api/valuation/').flush(ADOPTION_DTO);
    expect((result as { adoption: Adoption }).adoption.lines[0]).toEqual({
      productId: 'p-1',
      productName: 'Harina',
      unitAbbreviation: 'kg',
      reconciledQuantity: '3.0000',
      totalValue: '10.00',
      unitCost: '3.333333',
      declaredZero: false,
      source: 'Ingreso manual',
    });
  });

  it('reads the proposal with the warehouse breakdown and blockers', () => {
    let result: unknown;
    service.proposal().subscribe((p) => (result = p));
    http.expectOne('/api/valuation/proposal/').flush({
      lines: [
        {
          product_id: 'p-1',
          product_name: 'Harina',
          unit_abbreviation: 'kg',
          reconciled_quantity: '5.0000',
          warehouses: [{ warehouse_id: 'w-1', warehouse_name: 'Central', quantity: '5.0000' }],
        },
      ],
      blockers: [{ product_id: 'p-2', product_name: 'Azúcar', warehouse_id: 'w-1', warehouse_name: 'Central', quantity: '-1.0000' }],
    });
    const proposal = result as { lines: { warehouses: { warehouseName: string }[] }[]; blockers: { productName: string }[] };
    expect(proposal.lines[0].warehouses[0].warehouseName).toBe('Central');
    expect(proposal.blockers[0].productName).toBe('Azúcar');
  });

  it('adopts sending the idempotency key and null for a missing value or source (AC-03)', () => {
    service
      .adopt({
        adoptionId: 'a-1',
        lines: [{ productId: 'p-1', reconciledQuantity: '3.0000', totalValue: '', declaredZero: true, source: ' ' }],
      })
      .subscribe();
    const req = http.expectOne('/api/valuation/adopt/');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({
      adoption_id: 'a-1',
      lines: [{ product_id: 'p-1', reconciled_quantity: '3.0000', total_value: null, declared_zero: true, source: null }],
    });
    req.flush(ADOPTION_DTO, { status: 201, statusText: 'Created' });
  });

  it('maps a 400 to errors by line position (AC-03)', () => {
    let error: ValuationApiError | undefined;
    service.adopt({ adoptionId: 'a-1', lines: [] }).subscribe({ error: (e: ValuationApiError) => (error = e) });
    http
      .expectOne('/api/valuation/adopt/')
      .flush({ lines: [{}, { total_value: ['Pendiente'] }] }, { status: 400, statusText: 'Bad Request' });
    expect(error?.status).toBe(400);
    expect(error?.lineErrors[1].totalValue).toEqual(['Pendiente']);
  });

  it('maps 409 conflicts with their code and blockers (AC-04, AC-05, AC-06)', () => {
    let error: ValuationApiError | undefined;
    service.adopt({ adoptionId: 'a-1', lines: [] }).subscribe({ error: (e: ValuationApiError) => (error = e) });
    http.expectOne('/api/valuation/adopt/').flush(
      {
        detail: 'No se puede adoptar la valoración con stock negativo.',
        code: 'negative_stock',
        blockers: [{ product_id: 'p-2', product_name: 'Azúcar', warehouse_id: 'w-1', warehouse_name: 'Central', quantity: '-1.0000' }],
      },
      { status: 409, statusText: 'Conflict' },
    );
    expect(error?.code).toBe('negative_stock');
    expect(error?.blockers[0].warehouseName).toBe('Central');
  });

  it('reports a network failure with a friendly message', () => {
    let error: ValuationApiError | undefined;
    service.get().subscribe({ error: (e: ValuationApiError) => (error = e) });
    http.expectOne('/api/valuation/').error(new ProgressEvent('error'), { status: 0 });
    expect(error?.message).toContain('No se pudo conectar');
  });
});

describe('valuation helpers', () => {
  it('classifies a line: Pendiente, invalid, undeclared zero and ok (INV-03)', () => {
    expect(lineValueState('', false)).toBe('pending');
    expect(lineValueState('  ', false)).toBe('pending');
    expect(lineValueState('abc', false)).toBe('invalid');
    expect(lineValueState('1.234', false)).toBe('invalid');
    expect(lineValueState('0', false)).toBe('zero-undeclared');
    expect(lineValueState('0.00', false)).toBe('zero-undeclared');
    expect(lineValueState('12.5', false)).toBe('ok');
    expect(lineValueState('', true)).toBe('ok');
    expect(lineValueState('5', true)).toBe('invalid');
    expect(lineValueMessage('pending')).toContain('Pendiente');
    expect(lineValueMessage('ok')).toBeNull();
  });

  it('derives the unit cost with six decimals and half-up rounding like the server (AC-02, INV-02)', () => {
    expect(previewUnitCost('10.00', false, '3.0000')).toBe('3.333333');
    expect(previewUnitCost('20', false, '3')).toBe('6.666667');
    expect(previewUnitCost('0.01', false, '8.0000')).toBe('0.001250');
    expect(previewUnitCost('', true, '3.0000')).toBe('0.000000');
    expect(previewUnitCost('', false, '3.0000')).toBeNull();
    expect(previewUnitCost('10', false, '0')).toBeNull();
  });
});
