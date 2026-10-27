// Sidebar route metadata
export interface RouteInfo {
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
}
