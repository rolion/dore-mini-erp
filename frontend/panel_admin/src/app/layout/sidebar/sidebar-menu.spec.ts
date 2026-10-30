import routesFile from '../../../assets/data/routes.json';
import de from '../../../assets/i18n/de.json';
import en from '../../../assets/i18n/en.json';
import es from '../../../assets/i18n/es.json';
import { RouteInfo } from './sidebar.metadata';
import { visibleRoutes } from './sidebar.component';

function translate(dictionary: unknown, key: string): unknown {
  return key.split('.').reduce<unknown>((node, part) => (node as Record<string, unknown> | undefined)?.[part], dictionary);
}

describe('Sidebar menu (routes.json)', () => {
  const routes = routesFile.routes as RouteInfo[];

  it('has the business menu, Purchases, Inventory and Settings > Modules (AC-09, AC-20, AC-22, UI-01)', () => {
    expect(routes.length).toBe(9);

    const [dashboard, catalog, customer, orders, expenses, reports, purchases, inventory, settings] = routes;
    expect(routes.slice(0, 6).map((route) => route.module)).toEqual([
      'reporting', 'catalog', 'customers', 'sales', 'expenses', 'reporting',
    ]);
    expect(purchases.module).toBe('purchases');
    expect(purchases.submenu.map((item) => item.path)).toEqual([
      '/pocketbiz/purchases',
      '/pocketbiz/purchases/suppliers',
      '/pocketbiz/purchases/settings',
    ]);
    expect(purchases.submenu[0].title).toBe('MENUITEMS.PURCHASES.LIST.PURCHASES');
    expect(purchases.submenu[1].title).toBe('MENUITEMS.PURCHASES.LIST.SUPPLIERS');
    expect(inventory.module).toBe('inventory');
    expect(inventory.submenu.map((item) => item.path)).toEqual([
      '/pocketbiz/inventory',
      '/pocketbiz/inventory/stock',
      '/pocketbiz/inventory/configuration',
      '/pocketbiz/inventory/movements',
      '/pocketbiz/inventory/adjustments',
      '/pocketbiz/inventory/valuation',
      '/pocketbiz/inventory/settings',
    ]);
    expect(settings.module).toBeUndefined();
    expect(settings.submenu.map((item) => item.path)).toEqual(['/pocketbiz/settings/modules']);
    expect(dashboard.path).toBe('/pocketbiz/dashboard/main');
    expect(dashboard.submenu).toEqual([]);
    expect(dashboard.groupTitle).toBeFalse();

    expect(catalog.class).toBe('menu-toggle');
    expect(catalog.submenu.map((item) => item.path)).toEqual(['/pocketbiz/catalog/products']);

    expect(customer.path).toBe('/pocketbiz/customers');
    expect(customer.icon).toBe('users');
    expect(customer.class).toBe('');
    expect(customer.submenu).toEqual([]);
    expect(customer.groupTitle).toBeFalse();

    expect(orders.title).toBe('MENUITEMS.SALES.TEXT');
    expect(orders.icon).toBe('shopping-cart');
    expect(orders.class).toBe('menu-toggle');
    expect(orders.submenu.map((item) => item.path)).toEqual(['/pocketbiz/sales/orders', '/pocketbiz/sales/settings']);
    expect(orders.groupTitle).toBeFalse();

    expect(expenses.title).toBe('MENUITEMS.EXPENSES.TEXT');
    expect(expenses.icon).toBe('dollar-sign');
    expect(expenses.class).toBe('menu-toggle');
    expect(expenses.submenu.map((item) => item.path)).toEqual(['/pocketbiz/expenses', '/pocketbiz/expenses/categories']);
    expect(expenses.groupTitle).toBeFalse();

    expect(reports.path).toBe('/pocketbiz/reports');
    expect(reports.title).toBe('MENUITEMS.REPORTS.TEXT');
    expect(reports.icon).toBe('bar-chart-2');
    expect(reports.class).toBe('');
    expect(reports.submenu).toEqual([]);
    expect(reports.groupTitle).toBeFalse();
  });

  it('has a translation in en, es and de for every menu title (AC-09)', () => {
    const titles = routes.flatMap((route) => [route.title, ...route.submenu.map((item) => item.title)]);
    expect(titles.length).toBe(25);

    for (const [lang, dictionary] of [['en', en], ['es', es], ['de', de]] as const) {
      for (const title of titles) {
        expect(typeof translate(dictionary, title)).withContext(`${lang}: ${title}`).toBe('string');
      }
    }
    expect(translate(es, 'MENUITEMS.CATALOG.TEXT')).toBe('Catálogo');
    expect(translate(es, 'MENUITEMS.CATALOG.LIST.PRODUCT')).toBe('Producto');
    expect(translate(es, 'MENUITEMS.CUSTOMER.TEXT')).toBe('Cliente');
    expect(translate(es, 'MENUITEMS.SALES.LIST.ORDERS')).toBe('Pedidos');
    expect(translate(en, 'MENUITEMS.SALES.LIST.ORDERS')).toBe('Orders');
    expect(translate(de, 'MENUITEMS.SALES.LIST.ORDERS')).toBe('Bestellungen');
    expect(translate(es, 'MENUITEMS.SALES.LIST.SETTINGS')).toBe('Configuración');
    expect(translate(es, 'MENUITEMS.EXPENSES.TEXT')).toBe('Gastos');
    expect(translate(es, 'MENUITEMS.EXPENSES.LIST.CATEGORY')).toBe('Categorías');
    expect(translate(en, 'MENUITEMS.EXPENSES.TEXT')).toBe('Expenses');
    expect(translate(de, 'MENUITEMS.EXPENSES.LIST.CATEGORY')).toBe('Kategorien');
    expect(translate(es, 'MENUITEMS.REPORTS.TEXT')).toBe('Reportes');
    expect(translate(en, 'MENUITEMS.REPORTS.TEXT')).toBe('Reports');
    expect(translate(de, 'MENUITEMS.REPORTS.TEXT')).toBe('Berichte');
    expect(translate(es, 'MENUITEMS.SETTINGS.LIST.MODULES')).toBe('Módulos');
    expect(translate(es, 'MENUITEMS.PURCHASES.LIST.SUPPLIERS')).toBe('Proveedores');
    expect(translate(en, 'MENUITEMS.PURCHASES.LIST.SUPPLIERS')).toBe('Suppliers');
    expect(translate(de, 'MENUITEMS.PURCHASES.LIST.SUPPLIERS')).toBe('Lieferanten');
    expect(translate(es, 'MENUITEMS.INVENTORY.TEXT')).toBe('Inventario');
    expect(translate(es, 'MENUITEMS.INVENTORY.LIST.STOCK')).toBe('Existencias');
  });

  it('shows «Valoración» in the Inventory submenu only when Costeo is enabled (UI-01)', () => {
    const valuationPaths = (enabled: string[]) =>
      visibleRoutes(routes, new Set(enabled))
        .find((route) => route.module === 'inventory')
        ?.submenu.map((item) => item.path) ?? [];
    expect(valuationPaths(['inventory'])).not.toContain('/pocketbiz/inventory/valuation');
    expect(valuationPaths(['inventory', 'costing'])).toContain('/pocketbiz/inventory/valuation');
    expect(visibleRoutes(routes, new Set(['inventory', 'costing'])).find((r) => r.module === 'inventory')?.submenu.length)
      .toBe(7);
    expect(es.MENUITEMS.INVENTORY.LIST.VALUATION).toBe('Valoración');
  });
});
