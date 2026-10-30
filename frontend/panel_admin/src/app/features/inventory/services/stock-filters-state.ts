import { Injectable } from '@angular/core';
import { ActiveFilter, BalanceFilter, CategoryFilter, UseFilter } from '../models/stock';

export interface StockFilters {
  search: string;
  warehouseId: string;
  active: ActiveFilter;
  balance: BalanceFilter;
  category: CategoryFilter;
  canBuy: UseFilter;
  canSell: UseFilter;
}

export const DEFAULT_STOCK_FILTERS: StockFilters = {
  search: '',
  warehouseId: '',
  active: 'true',
  balance: '',
  category: '',
  canBuy: '',
  canSell: '',
};

/** Recuerda los filtros y la página de Existencias mientras dure la sesión, para restaurarlos al volver del detalle. */
@Injectable({
  providedIn: 'root',
})
export class StockFiltersState {
  filters: StockFilters = { ...DEFAULT_STOCK_FILTERS };
  page = 1;

  save(filters: StockFilters, page: number): void {
    this.filters = { ...filters };
    this.page = page;
  }

  reset(): void {
    this.filters = { ...DEFAULT_STOCK_FILTERS };
    this.page = 1;
  }
}
