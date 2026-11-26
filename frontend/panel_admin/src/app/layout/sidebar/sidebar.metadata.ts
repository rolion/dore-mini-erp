// Sidebar route metadata
export interface RouteInfo {
  /** Identifica el ítem de primer nivel para ordenarlo según el tipo de empresa (`module` no basta: se repite). */
  id?: string;
  path: string;
  title: string;
  iconType: string;
  icon: string;
  class: string;
  groupTitle: boolean;
  badge: string;
  badgeClass: string;
  submenu: RouteInfo[];
  /** Clave del módulo que habilita este ítem; sin clave, el ítem siempre se muestra. */
  module?: string;
  /** Solo lo ve quien administra la empresa (la API es la barrera real). */
  adminOnly?: boolean;
}
