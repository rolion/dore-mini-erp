/** Contenido estático de la landing (docs/design/specs/landing-pagina-principal.md). */

export interface NavAnchor {
  readonly id: string;
  readonly label: string;
}

export interface Benefit {
  readonly icon: string;
  readonly title: string;
  readonly text: string;
}

export interface FaqItem {
  readonly question: string;
  readonly answer: string;
}

export interface StatusRow {
  readonly label: string;
  readonly badge: string;
  readonly icon: string;
  readonly tone: 'success' | 'warning';
}

export interface FlowStep {
  readonly title: string;
  readonly text: string;
}

export const NAV_ANCHORS: readonly NavAnchor[] = [
  { id: 'que-puedes-controlar', label: 'Qué puedes controlar' },
  { id: 'como-funciona', label: 'Cómo funciona' },
  { id: 'planes', label: 'Planes' },
  { id: 'preguntas', label: 'Preguntas' },
];

export const FREE_LIMITS_NOTE =
  'Plan gratuito con límites: 1 producto, 1 cliente, 2 ventas y 2 gastos por día.';

export const RECOGNITION: readonly string[] = [
  'Pedidos que se pierden entre mensajes.',
  'Cobros que se olvidan.',
  'Gastos que nunca se anotan.',
];

export const BENEFITS: readonly Benefit[] = [
  {
    icon: 'fa-truck',
    title: 'Pedidos y entregas',
    text: 'Estados de cada pedido y canal de venta: WhatsApp, Facebook, Instagram, venta directa, feria u otro.',
  },
  {
    icon: 'fa-coins',
    title: 'Cobros',
    text: 'Pagos parciales y saldo pendiente por pedido.',
  },
  {
    icon: 'fa-receipt',
    title: 'Gastos',
    text: 'Registro por categoría y método de pago.',
  },
  {
    icon: 'fa-users',
    title: 'Clientes y productos',
    text: 'Historial de compras, precios y activar o desactivar.',
  },
];

export const CHANNEL_NOTE = 'WhatsApp, Facebook, Instagram, venta directa, feria u otro';

export const FLOW_STEPS: readonly FlowStep[] = [
  { title: 'Registras el pedido y su canal de venta', text: 'Cada pedido guarda de dónde vino.' },
  { title: 'Pedido listo, entrega pendiente', text: 'Ves el saldo por cobrar mientras se entrega.' },
  { title: 'Entregado y pagado', text: 'Cuando se entrega y se cobra, el pedido queda sin saldo.' },
];

export const READY_ROWS: readonly StatusRow[] = [
  { label: 'Entrega', badge: 'Listo', icon: 'fa-check-circle', tone: 'success' },
  { label: 'Cobro', badge: 'Pendiente', icon: 'fa-clock', tone: 'warning' },
];

export const DELIVERED_ROWS: readonly StatusRow[] = [
  { label: 'Entrega', badge: 'Entregado', icon: 'fa-truck', tone: 'success' },
  { label: 'Cobro', badge: 'Pagado', icon: 'fa-coins', tone: 'success' },
];

export const PERIODS: readonly string[] = ['Hoy', 'Esta semana', 'Este mes', 'Rango'];

export const PROFIT_NOTE =
  'Ventas − gastos registrados. Es una estimación, no la utilidad contable.';

export const GET_STARTED: readonly FlowStep[] = [
  { title: 'Crea tu cuenta', text: 'Con el nombre de tu empresa.' },
  { title: 'Registra tus productos, clientes y tu primer pedido', text: 'Empieza con lo que vendes hoy.' },
  { title: 'Mira tu resumen', text: 'Ventas, gastos y ganancia estimada.' },
];

export const FREE_PLAN_FEATURES: readonly string[] = [
  '1 producto',
  '1 cliente',
  '2 ventas y 2 gastos por día',
  'Dashboard y reportes de ventas y gastos',
];

export const FREE_PLAN_LIMIT_TEXT =
  'Al llegar al límite sigues viendo tus datos y puedes registrar de nuevo al día siguiente';

export const PRO_PLAN_FEATURE = 'Productos, clientes, ventas y gastos sin restricciones';

export const PRO_PAYMENT_LABEL = 'Pago disponible próximamente';

export const FAQ: readonly FaqItem[] = [
  {
    question: '¿Necesito instalar algo?',
    answer: 'Es una web: se usa desde el navegador del celular o de la computadora.',
  },
  {
    question: '¿Emite facturas o lleva inventario?',
    answer: 'No. Es control de pedidos, cobros y gastos.',
  },
  {
    question: '¿La ganancia es real?',
    answer: 'Es estimada: ventas menos gastos registrados.',
  },
  {
    question: '¿Puedo agregar a mi equipo?',
    answer: 'Hoy no se hace desde la pantalla.',
  },
  {
    question: '¿Qué pasa si olvido mi contraseña?',
    answer: 'Aún no hay recuperación automática.',
  },
  {
    question: '¿Qué pasa al llegar al límite del plan gratuito?',
    answer:
      'No puedes ingresar más datos hasta el día siguiente o hasta pasar a Pro; tus datos siguen visibles.',
  },
];
