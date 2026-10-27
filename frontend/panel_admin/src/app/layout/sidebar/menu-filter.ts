import { RouteInfo } from './sidebar.metadata';

/**
 * Menú visible para los módulos habilitados de la empresa. Un ítem se muestra si no declara módulo o si el suyo
 * (o el del grupo que lo contiene) está habilitado; un grupo sin hijos visibles se oculta. Mientras no se conocen
 * los módulos (`null`) solo se ven los ítems sin módulo.
 */
export function filterMenu(
  items: readonly RouteInfo[],
  enabled: ReadonlySet<string> | null,
  inherited?: string,
): RouteInfo[] {
  const visible: RouteInfo[] = [];
  for (const item of items) {
    if (!item) {
      continue;
    }
    const module = item.module ?? inherited;
    if (module && !(enabled !== null && enabled.has(module))) {
      continue;
    }
    if (item.submenu.length === 0) {
      visible.push(item);
      continue;
    }
    const submenu = filterMenu(item.submenu, enabled, module);
    if (submenu.length > 0) {
      visible.push({ ...item, submenu });
    }
  }
  return visible;
}
