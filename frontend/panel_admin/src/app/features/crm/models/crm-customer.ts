/** Fila del listado CRM tal como la entrega `GET /api/crm/customers/`. */
export interface CrmCustomerDto {
  customer_id: string;
  display_name: string;
  phone: string;
  last_purchase_at: string | null;
  order_count: number;
  outstanding_amount: string;
  currency: string;
}

export interface CrmListMeta {
  sales_enabled: boolean;
  warehouse_filter_enabled: boolean;
}

export interface CrmCustomerPageDto {
  count: number;
  next: string | null;
  previous: string | null;
  results: CrmCustomerDto[];
  meta: CrmListMeta;
}

export interface CrmCustomer {
  id: string;
  name: string;
  phone: string;
  /** Fecha ISO (`YYYY-MM-DD`) del último pedido válido; `null` si nunca compró. */
  lastPurchaseAt: string | null;
  orderCount: number;
  /** Importe tal como lo entrega el servidor (Decimal como texto). */
  outstandingAmount: string;
  currency: string;
}

export interface CrmCustomerPage {
  count: number;
  results: CrmCustomer[];
  meta: CrmListMeta;
}

export interface CrmListParams {
  search?: string;
  warehouseId?: string;
  page?: number;
  pageSize?: number;
}
