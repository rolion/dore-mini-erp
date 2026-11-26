import { RouteInfo } from './sidebar.metadata';

/**
 * Orden del menú según el tipo de empresa elegido al registrarse. El tipo no limita nada: solo ordena y ubica ítems;
 * qué se muestra lo decide, como siempre, el filtro por módulos habilitados y rol.
 */
interface MenuLayout {
  /** Ítems de primer nivel (`RouteInfo.id`) en el orden en que van arriba; el resto va después, antes de Ajustes. */
  order: readonly string[];
  /** Ítem que se muestra como subítem de otro (p. ej. Cotizaciones como «Presupuestos» dentro de Odontología). */
  nest?: { id: string; under: string; title: string };
}

const SETTINGS_ID = 'settings';

const SERVICES_ORDER = [
  'dashboard', 'catalog', 'customers', 'quotations', 'receivables', 'agenda', 'personnel',
  'accounting', 'expenses', 'reports',
] as const;

const LAYOUTS: Readonly<Record<string, MenuLayout>> = {
  compraventa: {
    order: [
      'dashboard', 'catalog', 'customers', 'sales', 'purchases', 'inventory', 'accounting', 'expenses', 'reports',
    ],
  },
  servicios: { order: SERVICES_ORDER },
  odontologia: {
    order: [
      'dashboard', 'catalog', 'customers', 'dentistry', 'receivables', 'agenda', 'personnel',
      'accounting', 'expenses', 'reports',
    ],
    nest: { id: 'quotations', under: 'dentistry', title: 'MENUITEMS.DENTISTRY.BUDGETS' },
  },
};

/**
 * Reordena el menú para el tipo de empresa. Con tipo `general`, ausente o desconocido (sesiones guardadas antes del
 * tipo) devuelve el orden original. Lo que el diseño no nombra va después, en su orden original y antes de Ajustes,
 * así un módulo habilitado más tarde siempre aparece. Se aplica sobre los ítems ya visibles: si el ítem que debería
 * contener a otro no está visible, este último queda como ítem propio para no perder el acceso.
 */
export function arrangeRoutes(routes: RouteInfo[], companyType: string | null | undefined): RouteInfo[] {
  const layout = companyType ? LAYOUTS[companyType] : undefined;
  if (!layout) {
    return routes;
  }
  const hasHost = routes.some((item) => item.id === layout.nest?.under);
  const nested = layout.nest && hasHost ? routes.find((item) => item.id === layout.nest?.id) : undefined;
  const rest = routes.filter((item) => item !== nested);
  const rank = (item: RouteInfo): number => {
    if (item.id === SETTINGS_ID) {
      return Number.MAX_SAFE_INTEGER;
    }
    const index = layout.order.indexOf(item.id ?? '');
    return index === -1 ? layout.order.length : index;
  };
  const arranged = rest
    .map((item, position) => ({ item, position }))
    .sort((a, b) => rank(a.item) - rank(b.item) || a.position - b.position)
    .map(({ item }) => item);
  if (!layout.nest || !nested) {
    return arranged;
  }
  return arranged.map((item) =>
    item.id === layout.nest?.under
      ? { ...item, submenu: [...item.submenu, ...nested.submenu.map((sub) => budgetItem(sub, nested, layout.nest))] }
      : item
  );
}

/** El subítem de Cotizaciones pasa a Odontología conservando su módulo, para que siga dependiendo de él. */
function budgetItem(sub: RouteInfo, parent: RouteInfo, nest: MenuLayout['nest']): RouteInfo {
  return { ...sub, title: nest?.title ?? sub.title, module: parent.module };
}
