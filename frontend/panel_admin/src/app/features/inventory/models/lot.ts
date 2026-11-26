import { tr } from '../../../core/i18n/translate';
import { StockUnit, StockUnitDto } from './stock';

export type LotStatus = 'refrigerating' | 'released';
export type LotStatusFilter = '' | LotStatus;

export const LOT_STATUS_LABELS: Record<LotStatus, string> = {
  get refrigerating() { return tr('INVENTORY.LOTS.EN_REFRIGERACION'); },
  get released() { return tr('INVENTORY.LOTS.LIBERADO'); },
};

/** Lote con su saldo físico y el disponible para empaque (solo si está liberado). Cantidades como texto decimal. */
export interface StockLot {
  id: string;
  code: string;
  status: LotStatus;
  lotDate: string;
  fiscalPeriodName: string;
  productId: string;
  productName: string;
  productActive: boolean;
  unit: StockUnit | null;
  warehouseId: string;
  warehouseName: string;
  physicalQuantity: string;
  availableQuantity: string;
  createdAt: string | null;
  releasedAt: string | null;
  releasedByName: string;
}

export interface StockLotDto {
  id: string;
  code: string;
  status: LotStatus;
  lot_date: string;
  fiscal_period_name: string;
  product_id: string;
  product_name: string;
  product_active: boolean;
  unit: StockUnitDto | null;
  warehouse_id: string;
  warehouse_name: string;
  physical_quantity: string;
  available_quantity: string;
  created_at: string | null;
  released_at: string | null;
  released_by_name: string;
}

export interface LotListParams {
  search?: string;
  productId?: string;
  warehouseId?: string;
  status?: LotStatus;
  withStock?: boolean;
  /** Página base 1. */
  page?: number;
  pageSize?: number;
}
