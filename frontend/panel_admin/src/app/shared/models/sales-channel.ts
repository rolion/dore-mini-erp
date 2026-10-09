/** Canal de venta del pedido; lo comparten Pedidos y Reportes (los códigos son los del servidor). */
export type SalesChannel = 'WHATSAPP' | 'FACEBOOK' | 'INSTAGRAM' | 'STORE' | 'FAIR' | 'OTHER';

export const SALES_CHANNELS: readonly SalesChannel[] = ['WHATSAPP', 'FACEBOOK', 'INSTAGRAM', 'STORE', 'FAIR', 'OTHER'];

export const SALES_CHANNEL_LABELS: Record<SalesChannel, string> = {
  WHATSAPP: 'WhatsApp',
  FACEBOOK: 'Facebook',
  INSTAGRAM: 'Instagram',
  STORE: 'Venta directa',
  FAIR: 'Feria',
  OTHER: 'Otro',
};
