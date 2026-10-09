import { convertToParamMap } from '@angular/router';

import {
  DEFAULT_FILTERS,
  ListState,
  SHORTCUTS,
  activeShortcut,
  hasActiveFilters,
  parseState,
  serializeState,
  statusesFor,
  toListParams,
} from './order-list-filters';

const BASE: ListState = { ...DEFAULT_FILTERS, page: 1 };

describe('order list filters', () => {
  describe('toListParams (AC-16, AC-23)', () => {
    it('sends only paging and the default ordering when nothing is filtered', () => {
      expect(toListParams(BASE, 10)).toEqual({ page: 1, pageSize: 10, ordering: '-order_date' });
    });

    it('maps "Pendientes de entrega" to the three open statuses ordered by expected delivery', () => {
      expect(toListParams({ ...BASE, statusKey: 'PENDING_DELIVERY' }, 10)).toEqual({
        page: 1,
        pageSize: 10,
        status: ['NEW', 'IN_PREPARATION', 'READY'],
        ordering: 'expected_delivery_date',
      });
    });

    it('maps "Por cobrar" to not-cancelled orders with balance', () => {
      expect(toListParams({ ...BASE, statusKey: 'NOT_CANCELLED', paymentKey: 'WITH_BALANCE' }, 10)).toEqual({
        page: 1,
        pageSize: 10,
        status: ['NEW', 'IN_PREPARATION', 'READY', 'DELIVERED'],
        hasBalance: true,
        ordering: '-order_date',
      });
    });

    it('maps a single status and a single payment status', () => {
      const params = toListParams({ ...BASE, statusKey: 'CANCELLED', paymentKey: 'PARTIAL', page: 3 }, 10);
      expect(params.status).toEqual(['CANCELLED']);
      expect(params.paymentStatus).toEqual(['PARTIAL']);
      expect(params.hasBalance).toBeUndefined();
      expect(params.page).toBe(3);
    });

    it('sends channel, customer and the date range with the chosen date field', () => {
      const params = toListParams(
        {
          ...BASE,
          channel: 'FAIR',
          customer: { id: 'c-1', name: 'Ana' },
          dateField: 'expected_delivery_date',
          dateFrom: '2026-10-01',
          dateTo: '2026-10-31',
        },
        10,
      );
      expect(params).toEqual(
        jasmine.objectContaining({
          salesChannel: 'FAIR',
          customerId: 'c-1',
          dateField: 'expected_delivery_date',
          dateFrom: '2026-10-01',
          dateTo: '2026-10-31',
        }),
      );
    });

    it('omits the date field when there is no date range', () => {
      const params = toListParams({ ...BASE, dateField: 'expected_delivery_date' }, 10);
      expect(params.dateField).toBeUndefined();
    });
  });

  it('expands status groups (AC-23)', () => {
    expect(statusesFor('ALL')).toBeUndefined();
    expect(statusesFor('NOT_CANCELLED')).toEqual(['NEW', 'IN_PREPARATION', 'READY', 'DELIVERED']);
    expect(statusesFor('READY')).toEqual(['READY']);
  });

  describe('URL round trip (AC-23)', () => {
    it('writes nothing for the default state', () => {
      const params = serializeState(BASE);
      expect(Object.values(params).every((value) => value === null)).toBeTrue();
    });

    it('serializes and parses every filter back', () => {
      const state: ListState = {
        statusKey: 'NOT_CANCELLED',
        paymentKey: 'WITH_BALANCE',
        channel: 'STORE',
        customer: { id: 'c-1', name: 'Ana Pérez' },
        dateField: 'expected_delivery_date',
        dateFrom: '2026-10-01',
        dateTo: '2026-10-31',
        page: 4,
      };
      const query = serializeState(state);
      const asParamMap = convertToParamMap(
        Object.fromEntries(Object.entries(query).filter(([, value]) => value !== null)) as Record<string, string>,
      );
      expect(parseState(asParamMap)).toEqual(state);
    });

    it('falls back to defaults for unknown or malformed values', () => {
      const state = parseState(
        convertToParamMap({ status: 'XX', pay: 'YY', channel: 'ZZ', date_field: 'created', page: 'abc' }),
      );
      expect(state).toEqual(BASE);
      expect(parseState(convertToParamMap({ page: '0' })).page).toBe(1);
      expect(parseState(convertToParamMap({ page: '2.5' })).page).toBe(1);
    });

    it('keeps the customer id even without a name', () => {
      expect(parseState(convertToParamMap({ customer: 'c-9' })).customer).toEqual({ id: 'c-9', name: '' });
    });
  });

  describe('shortcuts', () => {
    it('are the five of the design, only setting the delivery and payment filters (AC-23)', () => {
      expect(SHORTCUTS.map((s) => s.label)).toEqual([
        'Todos', 'Pendientes de entrega', 'Por cobrar', 'Entregados', 'Cancelados',
      ]);
    });

    it('detect which one matches the current filters', () => {
      for (const shortcut of SHORTCUTS) {
        expect(activeShortcut({ ...DEFAULT_FILTERS, statusKey: shortcut.statusKey, paymentKey: shortcut.paymentKey }))
          .toBe(shortcut.id);
      }
      expect(activeShortcut({ ...DEFAULT_FILTERS, statusKey: 'READY' })).toBeNull();
    });
  });

  it('knows when filters are active', () => {
    expect(hasActiveFilters(DEFAULT_FILTERS)).toBeFalse();
    expect(hasActiveFilters({ ...DEFAULT_FILTERS, channel: 'FAIR' })).toBeTrue();
    expect(hasActiveFilters({ ...DEFAULT_FILTERS, dateTo: '2026-10-01' })).toBeTrue();
    expect(hasActiveFilters({ ...DEFAULT_FILTERS, customer: { id: 'c', name: 'n' } })).toBeTrue();
  });
});
