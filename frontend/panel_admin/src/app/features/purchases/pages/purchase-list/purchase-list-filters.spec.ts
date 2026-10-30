import { convertToParamMap } from '@angular/router';
import {
  EMPTY_FILTERS,
  describeFilters,
  filtersFromParams,
  filtersToApi,
  filtersToQuery,
  hasActiveFilters,
  isRangeInvalid,
} from './purchase-list-filters';

describe('purchase list filters', () => {
  it('reads valid filters from the URL and ignores unknown values (AC-08)', () => {
    const filters = filtersFromParams(
      convertToParamMap({
        supplierId: 's-1',
        dateFrom: '2026-10-01',
        dateTo: 'mañana',
        status: 'confirmed',
        receptionStatus: 'zzz',
        paymentStatus: 'pending',
        q: '  FAC-1 ',
      }),
    );
    expect(filters).toEqual({
      supplierId: 's-1',
      dateFrom: '2026-10-01',
      dateTo: '',
      status: 'confirmed',
      receptionStatus: '',
      paymentStatus: 'pending',
      search: 'FAC-1',
    });
  });

  it('round-trips through the URL and omits empty filters (AC-08)', () => {
    const filters = { ...EMPTY_FILTERS, receptionStatus: 'received' as const, paymentStatus: 'pending' as const };
    const query = filtersToQuery(filters);
    expect(query).toEqual({ receptionStatus: 'received', paymentStatus: 'pending' });
    expect(filtersFromParams(convertToParamMap(query))).toEqual(filters);
    expect(filtersToQuery(EMPTY_FILTERS)).toEqual({});
  });

  it('maps to API parameters, leaving empty ones undefined (AC-02, AC-03)', () => {
    expect(filtersToApi({ ...EMPTY_FILTERS, status: 'confirmed', search: ' x ' })).toEqual({
      supplierId: undefined,
      dateFrom: undefined,
      dateTo: undefined,
      status: 'confirmed',
      receptionStatus: undefined,
      paymentStatus: undefined,
      search: 'x',
    });
  });

  it('detects active filters and an inverted date range (AC-08, AC-11)', () => {
    expect(hasActiveFilters(EMPTY_FILTERS)).toBeFalse();
    expect(hasActiveFilters({ ...EMPTY_FILTERS, search: '  ' })).toBeFalse();
    expect(hasActiveFilters({ ...EMPTY_FILTERS, status: 'draft' })).toBeTrue();
    expect(isRangeInvalid({ ...EMPTY_FILTERS, dateFrom: '2026-10-10', dateTo: '2026-10-01' })).toBeTrue();
    expect(isRangeInvalid({ ...EMPTY_FILTERS, dateFrom: '2026-10-10', dateTo: '2026-10-10' })).toBeFalse();
    expect(isRangeInvalid({ ...EMPTY_FILTERS, dateFrom: '2026-10-10' })).toBeFalse();
  });

  it('describes each active filter in Spanish (AC-09)', () => {
    const parts = describeFilters(
      { ...EMPTY_FILTERS, supplierId: 's-1', dateFrom: '2026-10-01', receptionStatus: 'received', paymentStatus: 'pending' },
      'Distribuidora Sur',
    );
    expect(parts).toEqual([
      'Proveedor: Distribuidora Sur',
      'Desde: 01/10/2026',
      'Recepción: Recibida',
      'Pago: Pago pendiente',
    ]);
  });
});
