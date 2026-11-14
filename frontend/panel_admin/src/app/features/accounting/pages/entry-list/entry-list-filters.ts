import { ParamMap, Params } from '@angular/router';
import { ENTRY_ORIGINS, EMPTY_ENTRY_FILTERS, EntryListFilters, EntryOrigin } from '../../models/entry';

export function filtersFromParams(params: ParamMap): EntryListFilters {
  const origin = params.get('origin');
  return {
    dateFrom: params.get('date_from') ?? '',
    dateTo: params.get('date_to') ?? '',
    accountId: params.get('account_id') ?? '',
    method: params.get('method') ?? '',
    origin: ENTRY_ORIGINS.includes(origin as EntryOrigin) ? (origin as EntryOrigin) : '',
  };
}

export function filtersToQuery(filters: EntryListFilters): Params {
  const query: Params = {};
  if (filters.dateFrom) query['date_from'] = filters.dateFrom;
  if (filters.dateTo) query['date_to'] = filters.dateTo;
  if (filters.accountId) query['account_id'] = filters.accountId;
  if (filters.method) query['method'] = filters.method;
  if (filters.origin) query['origin'] = filters.origin;
  return query;
}

export function hasActiveFilters(filters: EntryListFilters): boolean {
  return (Object.keys(EMPTY_ENTRY_FILTERS) as (keyof EntryListFilters)[]).some((key) => filters[key] !== '');
}

export function isRangeInvalid(filters: EntryListFilters): boolean {
  return !!filters.dateFrom && !!filters.dateTo && filters.dateFrom > filters.dateTo;
}
