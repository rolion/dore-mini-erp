import { sumMoney } from '../../../shared/utils/decimal-sum';
import { CustomerOrderSummary } from './customer';

/** Código de estado de entrega de un pedido cancelado; no cuenta en las cifras del perfil (INV-01). */
export const CANCELLED_STATUS = 'CANCELLED';

export interface CustomerPurchaseSummary {
  /** Fecha (`AAAA-MM-DD`) del pedido no cancelado más reciente; `null` si no hay ninguno. */
  lastPurchaseDate: string | null;
  /** Pedidos no cancelados. */
  orderCount: number;
  /** Suma de `total` de los pedidos no cancelados (texto decimal). */
  totalPurchased: string;
  /** Suma de `balance` de los pedidos no cancelados (texto decimal). */
  outstandingBalance: string;
  /** Hay saldo por cobrar (mayor que cero); se decide sobre el texto, sin coma flotante. */
  hasOutstandingBalance: boolean;
}

/** Cifras del perfil a partir de los pedidos cargados. Los cancelados no cuentan; la suma no usa coma flotante. */
export function summarizePurchases(orders: readonly CustomerOrderSummary[]): CustomerPurchaseSummary {
  const valid = orders.filter((order) => order.status !== CANCELLED_STATUS);
  const lastPurchaseDate = valid.reduce<string | null>(
    (latest, order) => (latest === null || order.date > latest ? order.date : latest),
    null,
  );
  const outstandingBalance = sumMoney(valid.map((order) => order.balance));
  return {
    lastPurchaseDate,
    orderCount: valid.length,
    totalPurchased: sumMoney(valid.map((order) => order.total)),
    outstandingBalance,
    hasOutstandingBalance: !outstandingBalance.startsWith('-') && /[1-9]/.test(outstandingBalance),
  };
}

/** Enlace de WhatsApp con solo los dígitos del teléfono; `null` si no hay dígitos. */
export function whatsappUrl(phone: string): string | null {
  const digits = phone.replace(/\D/g, '');
  return digits ? `https://wa.me/${digits}` : null;
}
