import { SALES_CHANNELS, SALES_CHANNEL_LABELS, SalesChannel } from '../../../shared/models/sales-channel';

// El canal de venta es un tipo compartido (lo usan Pedidos y Reportes); se reexporta para no cambiar los imports de Sales.
export { SALES_CHANNELS, SALES_CHANNEL_LABELS };
export type { SalesChannel };
export type OrderStatus = 'NEW' | 'IN_PREPARATION' | 'READY' | 'DELIVERED' | 'CANCELLED';
export type PaymentStatus = 'PENDING' | 'PARTIAL' | 'PAID' | 'REFUNDED';
export type PaymentMethod = 'CASH' | 'QR' | 'BANK_TRANSFER' | 'CARD' | 'OTHER';
/** Acciones de estado que el servidor declara disponibles para un pedido. */
export type OrderAction = 'prepare' | 'ready' | 'deliver' | 'cancel';

export const ORDER_STATUSES: readonly OrderStatus[] = ['NEW', 'IN_PREPARATION', 'READY', 'DELIVERED', 'CANCELLED'];
export const PAYMENT_STATUSES: readonly PaymentStatus[] = ['PENDING', 'PARTIAL', 'PAID', 'REFUNDED'];
export const PAYMENT_METHODS: readonly PaymentMethod[] = ['CASH', 'QR', 'BANK_TRANSFER', 'CARD', 'OTHER'];

export const ORDER_STATUS_LABELS: Record<OrderStatus, string> = {
  NEW: 'Nuevo',
  IN_PREPARATION: 'En preparación',
  READY: 'Listo',
  DELIVERED: 'Entregado',
  CANCELLED: 'Cancelado',
};

export const PAYMENT_STATUS_LABELS: Record<PaymentStatus, string> = {
  PENDING: 'Pendiente',
  PARTIAL: 'Parcial',
  PAID: 'Pagado',
  REFUNDED: 'Reembolsado',
};

export const PAYMENT_METHOD_LABELS: Record<PaymentMethod, string> = {
  CASH: 'Efectivo',
  QR: 'QR',
  BANK_TRANSFER: 'Transferencia',
  CARD: 'Tarjeta',
  OTHER: 'Otro',
};

/** Colores de la plantilla (`badge-outline col-*`); el texto y el icono siempre acompañan al color. */
export const ORDER_STATUS_COLORS: Record<OrderStatus, string> = {
  NEW: 'col-blue',
  IN_PREPARATION: 'col-orange',
  READY: 'col-indigo',
  DELIVERED: 'col-green',
  CANCELLED: 'col-red',
};

export const PAYMENT_STATUS_COLORS: Record<PaymentStatus, string> = {
  PENDING: 'col-orange',
  PARTIAL: 'col-cyan',
  PAID: 'col-green',
  REFUNDED: 'col-purple',
};

export interface OrderCustomer {
  id: string;
  name: string;
}

export interface OrderItem {
  id: string;
  productId: string;
  /** Snapshot del nombre al agregarlo. */
  productName: string;
  /** Importes como texto decimal ("35.00"): el navegador no opera con ellos. */
  unitPrice: string;
  quantity: number;
  subtotal: string;
}

export interface Payment {
  id: string;
  amount: string;
  paymentMethod: PaymentMethod;
  paymentDate: string;
  reference: string;
  createdAt: string;
}

/** Movimiento de la salida de inventario generada al entregar (cantidad como texto decimal). */
export interface StockOutputMovement {
  id: string;
  productId: string;
  productName: string;
  quantity: string;
  unit: string | null;
}

/** Salida de inventario del pedido entregado; `null` si no hubo o Inventario está deshabilitado. */
export interface StockOutput {
  reference: string;
  warehouseId: string;
  warehouseName: string;
  occurredAt: string;
  userName: string;
  movements: StockOutputMovement[];
}

export interface Order {
  id: string;
  /** Etiqueta corta para mostrar; el identificador es `id`. */
  code: string;
  customer: OrderCustomer | null;
  salesChannel: SalesChannel;
  orderDate: string;
  expectedDeliveryDate: string | null;
  deliveredDate: string | null;
  notes: string;
  status: OrderStatus;
  paymentStatus: PaymentStatus;
  items: OrderItem[];
  subtotal: string;
  discount: string;
  total: string;
  paidTotal: string;
  balance: string;
  payments: Payment[];
  cancellationReason: string;
  cancelledAt: string | null;
  /** El servidor decide qué se puede hacer; la interfaz no replica las reglas de estado. */
  editable: boolean;
  allowedTransitions: OrderAction[];
  canRegisterPayment: boolean;
  stockOutput: StockOutput | null;
  createdAt: string;
  updatedAt: string;
}

/** Almacén activo que puede recibir la salida. */
export interface DeliveryWarehouse {
  id: string;
  name: string;
  isDefault: boolean;
}

/** Línea de la vista previa: cantidades como texto decimal; `available`/`projected` son `null` sin almacén. */
export interface DeliveryLine {
  productId: string;
  productName: string;
  quantity: string;
  unit: string | null;
  available: string | null;
  projected: string | null;
  insufficient: boolean;
}

/** Foto informativa de la entrega: el servidor vuelve a validar al confirmar. */
export interface DeliveryPreview {
  inventoryEnabled: boolean;
  requiresStockOutput: boolean;
  allowNegativeStock: boolean;
  warehouses: DeliveryWarehouse[];
  warehouseId: string | null;
  lines: DeliveryLine[];
}

/** Línea sin existencia suficiente de un 409 `insufficient_stock`. */
export interface StockShortage {
  productName: string;
  unit: string | null;
  requested: string;
  available: string;
}

/** Fila de la lista de pedidos. */
export interface OrderSummary {
  id: string;
  code: string;
  customer: OrderCustomer | null;
  salesChannel: SalesChannel;
  orderDate: string;
  expectedDeliveryDate: string | null;
  status: OrderStatus;
  paymentStatus: PaymentStatus;
  total: string;
  paidTotal: string;
  balance: string;
}

/** Datos del pedido editables desde el formulario (ítems, descuento y pagos tienen sus propias acciones). */
export interface OrderInput {
  customerId: string | null;
  salesChannel: SalesChannel;
  orderDate: string;
  expectedDeliveryDate: string | null;
  notes: string;
}

export interface PaymentInput {
  amount: string;
  paymentMethod: PaymentMethod;
  paymentDate: string;
  reference: string;
}

export type OrderDateField = 'order_date' | 'expected_delivery_date';
export type OrderOrdering = '-order_date' | 'expected_delivery_date';

export interface OrderListParams {
  status?: OrderStatus[];
  paymentStatus?: PaymentStatus[];
  salesChannel?: SalesChannel;
  customerId?: string;
  dateField?: OrderDateField;
  dateFrom?: string;
  dateTo?: string;
  hasBalance?: boolean;
  ordering?: OrderOrdering;
  /** Página base 1. */
  page?: number;
  pageSize?: number;
}

/** Formas de respuesta de la API (snake_case). */
export interface OrderItemDto {
  id: string;
  product_id: string;
  product_name: string;
  unit_price: string;
  quantity: number;
  subtotal: string;
}

export interface PaymentDto {
  id: string;
  amount: string;
  payment_method: PaymentMethod;
  payment_date: string;
  reference: string;
  created_at: string;
}

export interface OrderDto {
  id: string;
  code: string;
  customer: OrderCustomer | null;
  sales_channel: SalesChannel;
  order_date: string;
  expected_delivery_date: string | null;
  delivered_date: string | null;
  notes: string;
  status: OrderStatus;
  payment_status: PaymentStatus;
  items: OrderItemDto[];
  subtotal: string;
  discount: string;
  total: string;
  paid_total: string;
  balance: string;
  payments: PaymentDto[];
  cancellation_reason: string;
  cancelled_at: string | null;
  editable: boolean;
  allowed_transitions: OrderAction[];
  can_register_payment: boolean;
  stock_output: StockOutputDto | null;
  created_at: string;
  updated_at: string;
}

export interface StockOutputDto {
  reference: string;
  warehouse: { id: string; name: string };
  occurred_at: string;
  user_name: string;
  movements: {
    id: string;
    product: { id: string; name: string };
    quantity: string;
    unit: { abbreviation: string | null };
  }[];
}

export interface DeliveryPreviewDto {
  inventory_enabled: boolean;
  requires_stock_output: boolean;
  allow_negative_stock: boolean;
  warehouses: { id: string; name: string; is_default: boolean }[];
  warehouse_id: string | null;
  lines: {
    product: { id: string; name: string };
    quantity: string;
    unit: { abbreviation: string | null };
    available: string | null;
    projected: string | null;
    insufficient: boolean;
  }[];
}

export interface OrderSummaryDto {
  id: string;
  code: string;
  customer: OrderCustomer | null;
  sales_channel: SalesChannel;
  order_date: string;
  expected_delivery_date: string | null;
  status: OrderStatus;
  payment_status: PaymentStatus;
  total: string;
  paid_total: string;
  balance: string;
}

/** Campos que el servidor puede señalar en un error de validación (en camelCase, como el resto del modelo). */
export type OrderErrorField =
  | 'customerId'
  | 'salesChannel'
  | 'orderDate'
  | 'expectedDeliveryDate'
  | 'notes'
  | 'productId'
  | 'quantity'
  | 'discount'
  | 'deliveredDate'
  | 'warehouseId'
  | 'reason'
  | 'amount'
  | 'paymentMethod'
  | 'paymentDate'
  | 'reference';

export type FieldErrors = Partial<Record<OrderErrorField, string[]>>;

export class OrderApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly fieldErrors: FieldErrors = {},
  ) {
    super(message);
    this.name = 'OrderApiError';
  }
}

/** El pedido no admite la acción en su estado actual (409 con `code` y mensaje del servidor). */
export class OrderRuleError extends OrderApiError {
  constructor(
    message: string,
    readonly code: string,
    /** Líneas sin existencia de un 409 `insufficient_stock` (vacío en otros conflictos). */
    readonly shortages: StockShortage[] = [],
    readonly warehouseName: string = '',
  ) {
    super(message, 409);
    this.name = 'OrderRuleError';
  }
}

/** Fecha local de hoy como `AAAA-MM-DD` (valor inicial editable de los campos de fecha). */
export function todayIso(now: Date = new Date()): string {
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${now.getFullYear()}-${month}-${day}`;
}

/** El servidor siempre entrega los importes con 2 decimales, así que "sin saldo" es exactamente "0.00". */
export const ZERO_AMOUNT = '0.00';

export function hasBalance(order: { balance: string }): boolean {
  return order.balance !== ZERO_AMOUNT;
}

/** Cantidad del servidor ("4.0000") sin ceros decimales sobrantes ("4", "2.5"). */
export function formatQuantity(value: string): string {
  return value.includes('.') ? value.replace(/\.?0+$/, '') : value;
}
