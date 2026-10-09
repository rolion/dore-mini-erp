// API pública de la feature: lo único que otras features pueden importar.
export type { Order, OrderSummary } from './models/order';
export { OrdersApiService } from './services/orders-api.service';
export type { OrderStatus, PaymentStatus } from './models/order';
export { ORDER_STATUS_LABELS, PAYMENT_STATUS_LABELS } from './models/order';
export { OrderStatusBadgeComponent } from './components/order-status-badge/order-status-badge.component';
export { PaymentStatusBadgeComponent } from './components/payment-status-badge/payment-status-badge.component';
