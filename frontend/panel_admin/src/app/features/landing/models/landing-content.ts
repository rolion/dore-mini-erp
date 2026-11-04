import { tr } from '../../../core/i18n/translate';
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
  { id: 'que-puedes-controlar', get label() { return tr('LANDING.LANDING_CONTENT.QUE_PUEDES_CONTROLAR'); } },
  { id: 'como-funciona', get label() { return tr('LANDING.LANDING_CONTENT.COMO_FUNCIONA'); } },
  { id: 'planes', get label() { return tr('LANDING.LANDING_CONTENT.PLANES'); } },
  { id: 'preguntas', get label() { return tr('LANDING.LANDING_CONTENT.PREGUNTAS'); } },
];

export const FREE_LIMITS_NOTE = (): string => tr('LANDING.LANDING_CONTENT.PLAN_GRATUITO_CON_LIMITES_1');

export const RECOGNITION = (): readonly string[] => [
  tr('LANDING.LANDING_CONTENT.PEDIDOS_QUE_SE_PIERDEN_ENTRE'),
  tr('LANDING.LANDING_CONTENT.COBROS_QUE_SE_OLVIDAN'),
  tr('LANDING.LANDING_CONTENT.GASTOS_QUE_NUNCA_SE_ANOTAN'),
];

export const BENEFITS: readonly Benefit[] = [
  {
    icon: 'fa-truck',
    get title() { return tr('LANDING.LANDING_CONTENT.PEDIDOS_Y_ENTREGAS'); },
    get text() { return tr('LANDING.LANDING_CONTENT.ESTADOS_DE_CADA_PEDIDO_Y'); },
  },
  {
    icon: 'fa-coins',
    get title() { return tr('LANDING.LANDING_CONTENT.COBROS'); },
    get text() { return tr('LANDING.LANDING_CONTENT.PAGOS_PARCIALES_Y_SALDO_PENDIENTE'); },
  },
  {
    icon: 'fa-receipt',
    get title() { return tr('LANDING.LANDING_CONTENT.GASTOS'); },
    get text() { return tr('LANDING.LANDING_CONTENT.REGISTRO_POR_CATEGORIA_Y_METODO'); },
  },
  {
    icon: 'fa-users',
    get title() { return tr('LANDING.LANDING_CONTENT.CLIENTES_Y_PRODUCTOS'); },
    get text() { return tr('LANDING.LANDING_CONTENT.HISTORIAL_DE_COMPRAS_PRECIOS_Y'); },
  },
];

export const CHANNEL_NOTE = (): string => tr('LANDING.LANDING_CONTENT.WHATSAPP_FACEBOOK_INSTAGRAM_VENTA_DIRECTA');

export const FLOW_STEPS: readonly FlowStep[] = [
  { get title() { return tr('LANDING.LANDING_CONTENT.REGISTRAS_EL_PEDIDO_Y_SU'); }, get text() { return tr('LANDING.LANDING_CONTENT.CADA_PEDIDO_GUARDA_DE_DONDE'); } },
  { get title() { return tr('LANDING.LANDING_CONTENT.PEDIDO_LISTO_ENTREGA_PENDIENTE'); }, get text() { return tr('LANDING.LANDING_CONTENT.VES_EL_SALDO_POR_COBRAR'); } },
  { get title() { return tr('LANDING.LANDING_CONTENT.ENTREGADO_Y_PAGADO'); }, get text() { return tr('LANDING.LANDING_CONTENT.CUANDO_SE_ENTREGA_Y_SE'); } },
];

export const READY_ROWS: readonly StatusRow[] = [
  { get label() { return tr('LANDING.LANDING_CONTENT.ENTREGA'); }, get badge() { return tr('CUSTOMERS.CUSTOMER_PURCHASE_HISTORY.LISTO'); }, icon: 'fa-check-circle', tone: 'success' },
  { get label() { return tr('LANDING.LANDING_CONTENT.COBRO'); }, get badge() { return tr('INVENTORY.VALUATION.PENDIENTE'); }, icon: 'fa-clock', tone: 'warning' },
];

export const DELIVERED_ROWS: readonly StatusRow[] = [
  { get label() { return tr('LANDING.LANDING_CONTENT.ENTREGA'); }, get badge() { return tr('CUSTOMERS.CUSTOMER_PURCHASE_HISTORY.ENTREGADO'); }, icon: 'fa-truck', tone: 'success' },
  { get label() { return tr('LANDING.LANDING_CONTENT.COBRO'); }, get badge() { return tr('CUSTOMERS.CUSTOMER_PURCHASE_HISTORY.PAGADO'); }, icon: 'fa-coins', tone: 'success' },
];

export const PERIODS = (): readonly string[] => [tr('LANDING.LANDING_CONTENT.HOY'), tr('LANDING.LANDING_CONTENT.ESTA_SEMANA'), tr('EXPENSES.EXPENSE_LIST.ESTE_MES'), tr('LANDING.LANDING_CONTENT.RANGO')];

export const PROFIT_NOTE = (): string => tr('LANDING.LANDING_CONTENT.VENTAS_GASTOS_REGISTRADOS_ES_UNA');

export const GET_STARTED: readonly FlowStep[] = [
  { get title() { return tr('LANDING.LANDING_CONTENT.CREA_TU_CUENTA'); }, get text() { return tr('LANDING.LANDING_CONTENT.CON_EL_NOMBRE_DE_TU'); } },
  { get title() { return tr('LANDING.LANDING_CONTENT.REGISTRA_TUS_PRODUCTOS_CLIENTES_Y'); }, get text() { return tr('LANDING.LANDING_CONTENT.EMPIEZA_CON_LO_QUE_VENDES'); } },
  { get title() { return tr('LANDING.LANDING_CONTENT.MIRA_TU_RESUMEN'); }, get text() { return tr('LANDING.LANDING_CONTENT.VENTAS_GASTOS_Y_GANANCIA_ESTIMADA'); } },
];

export const FREE_PLAN_FEATURES = (): readonly string[] => [
  tr('LANDING.LANDING_CONTENT.FREE_PRODUCT'),
  tr('LANDING.LANDING_CONTENT.FREE_CUSTOMER'),
  tr('LANDING.LANDING_CONTENT.FREE_LIMITS'),
  tr('LANDING.LANDING_CONTENT.DASHBOARD_Y_REPORTES_DE_VENTAS'),
];

export const FREE_PLAN_LIMIT_TEXT = (): string => tr('LANDING.LANDING_CONTENT.AL_LLEGAR_AL_LIMITE_SIGUES');

export const PRO_PLAN_FEATURE = (): string => tr('LANDING.LANDING_CONTENT.PRODUCTOS_CLIENTES_VENTAS_Y_GASTOS');

export const PRO_PAYMENT_LABEL = (): string => tr('LANDING.LANDING_CONTENT.PAGO_DISPONIBLE_PROXIMAMENTE');

export const FAQ: readonly FaqItem[] = [
  {
    get question() { return tr('LANDING.LANDING_CONTENT.NECESITO_INSTALAR_ALGO'); },
    get answer() { return tr('LANDING.LANDING_CONTENT.ES_UNA_WEB_SE_USA'); },
  },
  {
    get question() { return tr('LANDING.LANDING_CONTENT.EMITE_FACTURAS_O_LLEVA_INVENTARIO'); },
    get answer() { return tr('LANDING.LANDING_CONTENT.NO_ES_CONTROL_DE_PEDIDOS'); },
  },
  {
    get question() { return tr('LANDING.LANDING_CONTENT.LA_GANANCIA_ES_REAL'); },
    get answer() { return tr('LANDING.LANDING_CONTENT.ES_ESTIMADA_VENTAS_MENOS_GASTOS'); },
  },
  {
    get question() { return tr('LANDING.LANDING_CONTENT.PUEDO_AGREGAR_A_MI_EQUIPO'); },
    get answer() { return tr('LANDING.LANDING_CONTENT.HOY_NO_SE_HACE_DESDE'); },
  },
  {
    get question() { return tr('LANDING.LANDING_CONTENT.QUE_PASA_SI_OLVIDO_MI'); },
    get answer() { return tr('LANDING.LANDING_CONTENT.AUN_NO_HAY_RECUPERACION_AUTOMATICA'); },
  },
  {
    get question() { return tr('LANDING.LANDING_CONTENT.QUE_PASA_AL_LLEGAR_AL'); },
    get answer() { return tr('LANDING.LANDING_CONTENT.NO_PUEDES_INGRESAR_MAS_DATOS'); },
  },
];
