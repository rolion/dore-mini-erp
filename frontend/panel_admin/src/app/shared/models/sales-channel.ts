import { tr } from '../../core/i18n/translate';
/** Canal de venta del pedido; lo comparten Pedidos y Reportes (los códigos son los del servidor). */
export type SalesChannel = 'WHATSAPP' | 'FACEBOOK' | 'INSTAGRAM' | 'STORE' | 'FAIR' | 'OTHER';

export const SALES_CHANNELS: readonly SalesChannel[] = ['WHATSAPP', 'FACEBOOK', 'INSTAGRAM', 'STORE', 'FAIR', 'OTHER'];

export const SALES_CHANNEL_LABELS: Record<SalesChannel, string> = {
  WHATSAPP: 'WhatsApp',
  FACEBOOK: 'Facebook',
  INSTAGRAM: 'Instagram',
  get STORE() { return tr('SHARED.SALES_CHANNEL.VENTA_DIRECTA'); },
  get FAIR() { return tr('SHARED.SALES_CHANNEL.FERIA'); },
  get OTHER() { return tr('EXPENSES.EXPENSE.OTRO'); },
};
