import routesFile from '../../../assets/data/routes.json';
import { arrangeRoutes } from './menu-layout';
import { RouteInfo } from './sidebar.metadata';
import { visibleRoutes } from './sidebar.component';

const routes = routesFile.routes as RouteInfo[];
const ids = (items: RouteInfo[]): (string | undefined)[] => items.map((item) => item.id);
const everyModule = new Set(routes.map((r) => r.module).filter((m): m is string => !!m));

describe('arrangeRoutes (menu por tipo de empresa)', () => {
  it('every top-level item of routes.json has a unique id', () => {
    expect(routes.every((route) => !!route.id)).toBeTrue();
    expect(new Set(ids(routes)).size).toBe(routes.length);
  });

  it('orders the buying-and-selling menu and leaves Settings last (AC-09)', () => {
    const arranged = arrangeRoutes(visibleRoutes(routes, everyModule), 'compraventa');
    expect(ids(arranged).slice(0, 9)).toEqual([
      'dashboard', 'catalog', 'customers', 'sales', 'purchases', 'inventory', 'accounting', 'expenses', 'reports',
    ]);
    expect(ids(arranged).at(-1)).toBe('settings');
  });

  it('orders the services menu with Quotations as its own item (AC-09, AC-10)', () => {
    const arranged = arrangeRoutes(visibleRoutes(routes, everyModule), 'servicios');
    expect(ids(arranged).slice(0, 10)).toEqual([
      'dashboard', 'catalog', 'customers', 'quotations', 'receivables', 'agenda', 'personnel',
      'accounting', 'expenses', 'reports',
    ]);
    expect(ids(arranged).at(-1)).toBe('settings');
  });

  it('puts items enabled later and missing from the layout before Settings (AC-09)', () => {
    const arranged = arrangeRoutes(visibleRoutes(routes, everyModule), 'servicios');
    // En servicios, Ventas / Compras / Inventario / Producción / Odontología no están en el diseño: van al final, antes de Ajustes.
    const tail = ids(arranged).slice(10, -1);
    expect(tail).toEqual(['dentistry', 'sales', 'purchases', 'inventory', 'production']);
  });

  it('shows Quotations as «Presupuestos» inside Dentistry for dentistry companies (AC-10)', () => {
    const arranged = arrangeRoutes(visibleRoutes(routes, everyModule), 'odontologia');
    expect(ids(arranged)).not.toContain('quotations');
    const dentistry = arranged.find((item) => item.id === 'dentistry');
    expect(dentistry?.submenu.map((item) => item.path)).toEqual([
      '/pocketbiz/dentistry/patients', '/pocketbiz/dentistry/appointments', '/pocketbiz/quotations/proformas',
    ]);
    expect(dentistry?.submenu[2].title).toBe('MENUITEMS.DENTISTRY.BUDGETS');
    expect(ids(arranged).slice(0, 4)).toEqual(['dashboard', 'catalog', 'customers', 'dentistry']);
  });

  it('hides «Presupuestos» when the Quotations module is off (AC-10)', () => {
    const enabled = new Set([...everyModule].filter((module) => module !== 'quotations'));
    const arranged = arrangeRoutes(visibleRoutes(routes, enabled), 'odontologia');
    expect(arranged.find((item) => item.id === 'dentistry')?.submenu.map((item) => item.path)).toEqual([
      '/pocketbiz/dentistry/patients', '/pocketbiz/dentistry/appointments',
    ]);
  });

  it('does not lose Quotations when Dentistry is off (AC-10)', () => {
    const enabled = new Set([...everyModule].filter((module) => module !== 'dentistry'));
    const arranged = arrangeRoutes(visibleRoutes(routes, enabled), 'odontologia');
    expect(ids(arranged)).toContain('quotations');
  });

  it('does not mutate the original routes', () => {
    const before = JSON.stringify(routes);
    arrangeRoutes(routes, 'odontologia');
    arrangeRoutes(routes, 'servicios');
    expect(JSON.stringify(routes)).toBe(before);
  });

  it('keeps the current order for general, missing or unknown types (AC-11, EDGE-01)', () => {
    for (const type of ['general', undefined, null, '', 'otro']) {
      expect(arrangeRoutes(routes, type)).toBe(routes);
    }
  });
});
