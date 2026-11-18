import { Injectable } from '@angular/core';
import { EMPTY_JOURNAL_FILTERS, JournalFilters } from '../models/journal';

/** Filtros y página de Movimientos en memoria: se restauran al volver desde un detalle. */
@Injectable({ providedIn: 'root' })
export class JournalFiltersState {
  filters: JournalFilters = EMPTY_JOURNAL_FILTERS;
  pageIndex = 0;

  remember(filters: JournalFilters, pageIndex: number): void {
    this.filters = filters;
    this.pageIndex = pageIndex;
  }
}
