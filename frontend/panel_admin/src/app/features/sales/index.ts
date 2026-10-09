// API pública de la feature: lo único que otras features pueden importar.
export type { Order, OrderSummary } from './models/order';
export { OrdersApiService } from './services/orders-api.service';
