import routesFile from '../../../assets/data/routes.json';
import en from '../../../assets/i18n/en.json';
import es from '../../../assets/i18n/es.json';
import pt from '../../../assets/i18n/pt.json';
import { RouteInfo } from './sidebar.metadata';
import { visibleRoutes } from './sidebar.component';

function translate(dictionary: unknown, key: string): unknown {
  return key.split('.').reduce<unknown>((node, part) => (node as Record<string, unknown> | undefined)?.[part], dictionary);
}

describe('Sidebar menu (routes.json)', () => {
  const routes = routesFile.routes as RouteInfo[];

  it('has the business menu, Dentistry, Purchases, Inventory and Settings > Modules', () => {
    expect(routes.length).toBe(16);

    const [dashboard, catalog, customer, dentistry, orders, expenses, reports, purchases, inventory, production, accounting, settings, agenda, personnel, quotations, receivables] = routes;
    expect(routes.slice(0, 7).map((route) => route.module)).toEqual([
      'reporting', 'catalog', 'customers', 'dentistry', 'sales', 'expenses', 'reporting',
    ]);
    expect(dentistry.submenu.map((item) => item.path)).toEqual(['/pocketbiz/dentistry/patients', '/pocketbiz/dentistry/appointments']);
    expect(visibleRoutes(routes, new Set(['customers'])).some((route) => route.module === 'dentistry')).toBeFalse();
    expect(visibleRoutes(routes, new Set(['customers', 'dentistry'])).some((route) => route.module === 'dentistry')).toBeTrue();
    expect(agenda.module).toBe('agenda');
    expect(agenda.submenu.map((item) => item.path)).toEqual([
      '/pocketbiz/agenda/citas', '/pocketbiz/agenda/configuracion/horarios',
    ]);
    expect(quotations.module).toBe('quotations');
    expect(quotations.submenu.map((item) => item.path)).toEqual(['/pocketbiz/quotations/proformas']);
    expect(receivables.module).toBe('receivables');
    // SRV-01: Cobros pasa a ser un grupo porque ahora tiene una segunda pantalla (la configuración contable).
    expect(receivables.submenu.map((item) => item.path)).toEqual([
      '/pocketbiz/receivables', '/pocketbiz/receivables/settings',
    ]);
    expect(personnel.module).toBe('personnel');
    expect(personnel.submenu.map((item) => item.path)).toEqual([
      '/pocketbiz/personnel/professionals', '/pocketbiz/personnel/specialties',
    ]);
    expect(production.module).toBe('production');
    expect(purchases.module).toBe('purchases');
    expect(purchases.submenu.map((item) => item.path)).toEqual([
      '/pocketbiz/purchases',
      '/pocketbiz/purchases/suppliers',
      '/pocketbiz/purchases/reports/paid',
      '/pocketbiz/purchases/reports/payable',
      '/pocketbiz/purchases/settings',
    ]);
    expect(purchases.submenu[0].title).toBe('MENUITEMS.PURCHASES.LIST.PURCHASES');
    expect(purchases.submenu[1].title).toBe('MENUITEMS.PURCHASES.LIST.SUPPLIERS');
    expect(inventory.module).toBe('inventory');
    expect(inventory.submenu.map((item) => item.path)).toEqual([
      '/pocketbiz/inventory',
      '/pocketbiz/inventory/stock',
      '/pocketbiz/inventory/lots',
      '/pocketbiz/inventory/configuration',
      '/pocketbiz/inventory/movements',
      '/pocketbiz/inventory/adjustments',
      '/pocketbiz/inventory/valuation',
      '/pocketbiz/inventory/settings',
    ]);
    expect(accounting.module).toBe('accounting'); // el menú sigue al módulo; se configura desde Módulos (enlace del 409)
    expect(accounting.adminOnly).toBeTrue();
    expect(visibleRoutes(routes, new Set(['customers', 'accounting']), false).some((route) => route.adminOnly)).toBeFalse();
    expect(visibleRoutes(routes, new Set(['customers']), true).some((route) => route.title === 'MENUITEMS.ACCOUNTING.TEXT')).toBeFalse();
    expect(visibleRoutes(routes, new Set(['customers', 'accounting']), true).some((route) => route.title === 'MENUITEMS.ACCOUNTING.TEXT')).toBeTrue();
    expect(accounting.submenu.map((item) => item.path)).toEqual([
      '/pocketbiz/accounting/accounts', '/pocketbiz/accounting/journal', '/pocketbiz/accounting/balances', '/pocketbiz/accounting/cash-flow',
      '/pocketbiz/accounting/income-expense', '/pocketbiz/accounting/balance-sheet', '/pocketbiz/accounting/settings',
    ]); // Cuentas, Movimientos, Saldos, Flujo de dinero, Ingresos y egresos, Balance general, Configuración (AC-09, AC-10)
    expect(settings.module).toBeUndefined();
    expect(settings.submenu.map((item) => item.path)).toEqual(['/pocketbiz/settings/modules']);
    expect(dashboard.path).toBe('/pocketbiz/dashboard/main');
    expect(dashboard.submenu).toEqual([]);
    expect(dashboard.groupTitle).toBeFalse();

    expect(catalog.class).toBe('menu-toggle');
    expect(catalog.submenu.map((item) => item.path)).toEqual(['/pocketbiz/catalog/products', '/pocketbiz/catalog/services']);

    expect(customer.path).toBe('/pocketbiz/customers');
    expect(customer.icon).toBe('users');
    expect(customer.class).toBe('');
    expect(customer.submenu).toEqual([]);
    expect(customer.groupTitle).toBeFalse();

    expect(orders.title).toBe('MENUITEMS.SALES.TEXT');
    expect(orders.icon).toBe('shopping-cart');
    expect(orders.class).toBe('menu-toggle');
    expect(orders.submenu.map((item) => item.path)).toEqual(['/pocketbiz/sales/orders', '/pocketbiz/sales/reports/income', '/pocketbiz/sales/reports/receivable', '/pocketbiz/sales/import', '/pocketbiz/sales/settings']);
    const salesFor = (isAdmin: boolean) => visibleRoutes(routes, new Set(['sales']), isAdmin).find((route) => route.module === 'sales')!;
    expect(salesFor(true).submenu.map((item) => item.path)).toContain('/pocketbiz/sales/import');
    expect(salesFor(false).submenu.map((item) => item.path)).not.toContain('/pocketbiz/sales/import');
    expect(orders.groupTitle).toBeFalse();

    expect(expenses.title).toBe('MENUITEMS.EXPENSES.TEXT');
    expect(expenses.icon).toBe('dollar-sign');
    expect(expenses.class).toBe('menu-toggle');
    expect(expenses.submenu.map((item) => item.path)).toEqual(['/pocketbiz/expenses', '/pocketbiz/expenses/categories', '/pocketbiz/expenses/settings']);
    expect(expenses.groupTitle).toBeFalse();

    expect(reports.path).toBe('/pocketbiz/reports');
    expect(reports.title).toBe('MENUITEMS.REPORTS.TEXT');
    expect(reports.icon).toBe('bar-chart-2');
    expect(reports.class).toBe('');
    expect(reports.submenu).toEqual([]);
    expect(reports.groupTitle).toBeFalse();
  });

  it('has a translation in en, es and pt for every menu title (AC-09)', () => {
    const titles = routes.flatMap((route) => [route.title, ...route.submenu.map((item) => item.title)]);
    expect(titles.length).toBe(59);

    for (const [lang, dictionary] of [['en', en], ['es', es], ['pt', pt]] as const) {
      for (const title of titles) {
        expect(typeof translate(dictionary, title)).withContext(`${lang}: ${title}`).toBe('string');
      }
    }
    expect(translate(es, 'MENUITEMS.CATALOG.TEXT')).toBe('Catálogo');
    expect(translate(es, 'MENUITEMS.CATALOG.LIST.PRODUCT')).toBe('Producto');
    expect(translate(es, 'MENUITEMS.CUSTOMER.TEXT')).toBe('Cliente');
    expect(translate(es, 'MENUITEMS.SALES.LIST.ORDERS')).toBe('Pedidos');
    expect(translate(en, 'MENUITEMS.SALES.LIST.ORDERS')).toBe('Orders');
    expect(translate(pt, 'MENUITEMS.SALES.LIST.ORDERS')).toBe('Pedidos');
    expect(translate(es, 'MENUITEMS.SALES.LIST.SETTINGS')).toBe('Configuración');
    expect(translate(es, 'MENUITEMS.EXPENSES.TEXT')).toBe('Gastos');
    expect(translate(es, 'MENUITEMS.EXPENSES.LIST.CATEGORY')).toBe('Categorías');
    expect(translate(en, 'MENUITEMS.EXPENSES.TEXT')).toBe('Expenses');
    expect(translate(pt, 'MENUITEMS.EXPENSES.LIST.CATEGORY')).toBe('Categorias');
    expect(translate(es, 'MENUITEMS.REPORTS.TEXT')).toBe('Reportes');
    expect(translate(en, 'MENUITEMS.REPORTS.TEXT')).toBe('Reports');
    expect(translate(pt, 'MENUITEMS.REPORTS.TEXT')).toBe('Relatórios');
    expect(translate(es, 'MENUITEMS.SETTINGS.LIST.MODULES')).toBe('Módulos');
    expect(translate(es, 'MENUITEMS.PURCHASES.LIST.SUPPLIERS')).toBe('Proveedores');
    expect(translate(en, 'MENUITEMS.PURCHASES.LIST.SUPPLIERS')).toBe('Suppliers');
    expect(translate(pt, 'MENUITEMS.PURCHASES.LIST.SUPPLIERS')).toBe('Fornecedores');
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
      .toBe(8);
    expect(es.MENUITEMS.INVENTORY.LIST.VALUATION).toBe('Valoración');
  });

  it('shows Producción → Recetas only when the production module is enabled (DORE-PROD-001 AC-09, AC-10)', () => {
    const production = (enabled: string[]) => visibleRoutes(routes, new Set(enabled)).find((route) => route.module === 'production');
    expect(production(['catalog'])).toBeUndefined();
    const menu = production(['catalog', 'production']);
    expect(menu?.submenu.map((item) => item.path)).toEqual(['/pocketbiz/production/recipes', '/pocketbiz/production/orders', '/pocketbiz/production/settings']);
    expect(translate(es, 'MENUITEMS.PRODUCTION.TEXT')).toBe('Producción');
    expect(translate(en, 'MENUITEMS.PRODUCTION.LIST.RECIPES')).toBe('Recipes');
    expect(translate(pt, 'MENUITEMS.PRODUCTION.LIST.RECIPES')).toBe('Receitas');
    expect(translate(es, 'MENUITEMS.PRODUCTION.LIST.ORDERS')).toBe('Órdenes de producción');
    expect(translate(en, 'MENUITEMS.PRODUCTION.LIST.ORDERS')).toBe('Production orders');
    expect(translate(pt, 'MENUITEMS.PRODUCTION.LIST.ORDERS')).toBe('Ordens de produção');
  });
});
