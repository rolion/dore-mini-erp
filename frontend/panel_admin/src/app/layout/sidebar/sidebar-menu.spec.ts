import routesFile from '../../../assets/data/routes.json';
import de from '../../../assets/i18n/de.json';
import en from '../../../assets/i18n/en.json';
import es from '../../../assets/i18n/es.json';
import { RouteInfo } from './sidebar.metadata';

function translate(dictionary: unknown, key: string): unknown {
  return key.split('.').reduce<unknown>((node, part) => (node as Record<string, unknown> | undefined)?.[part], dictionary);
}

describe('Sidebar menu (routes.json)', () => {
  const routes = routesFile.routes as RouteInfo[];

  it('only has Dashboard, Catalog > Product, Customer, Orders, Expenses and Reports (AC-09, AC-20, AC-22)', () => {
    expect(routes.length).toBe(6);

    const [dashboard, catalog, customer, orders, expenses, reports] = routes;
    expect(dashboard.path).toBe('/dashboard/main');
    expect(dashboard.submenu).toEqual([]);
    expect(dashboard.groupTitle).toBeFalse();

    expect(catalog.class).toBe('menu-toggle');
    expect(catalog.submenu.map((item) => item.path)).toEqual(['/catalog/products']);

    expect(customer.path).toBe('/customers');
    expect(customer.icon).toBe('users');
    expect(customer.class).toBe('');
    expect(customer.submenu).toEqual([]);
    expect(customer.groupTitle).toBeFalse();

    expect(orders.path).toBe('/sales/orders');
    expect(orders.title).toBe('MENUITEMS.ORDERS.TEXT');
    expect(orders.icon).toBe('shopping-cart');
    expect(orders.class).toBe('');
    expect(orders.submenu).toEqual([]);
    expect(orders.groupTitle).toBeFalse();

    expect(expenses.title).toBe('MENUITEMS.EXPENSES.TEXT');
    expect(expenses.icon).toBe('dollar-sign');
    expect(expenses.class).toBe('menu-toggle');
    expect(expenses.submenu.map((item) => item.path)).toEqual(['/expenses', '/expenses/categories']);
    expect(expenses.groupTitle).toBeFalse();

    expect(reports.path).toBe('/reports');
    expect(reports.title).toBe('MENUITEMS.REPORTS.TEXT');
    expect(reports.icon).toBe('bar-chart-2');
    expect(reports.class).toBe('');
    expect(reports.submenu).toEqual([]);
    expect(reports.groupTitle).toBeFalse();
  });

  it('has a translation in en, es and de for every menu title (AC-09)', () => {
    const titles = routes.flatMap((route) => [route.title, ...route.submenu.map((item) => item.title)]);
    expect(titles.length).toBe(9);

    for (const [lang, dictionary] of [['en', en], ['es', es], ['de', de]] as const) {
      for (const title of titles) {
        expect(typeof translate(dictionary, title)).withContext(`${lang}: ${title}`).toBe('string');
      }
    }
    expect(translate(es, 'MENUITEMS.CATALOG.TEXT')).toBe('Catálogo');
    expect(translate(es, 'MENUITEMS.CATALOG.LIST.PRODUCT')).toBe('Producto');
    expect(translate(es, 'MENUITEMS.CUSTOMER.TEXT')).toBe('Cliente');
    expect(translate(es, 'MENUITEMS.ORDERS.TEXT')).toBe('Pedidos');
    expect(translate(en, 'MENUITEMS.ORDERS.TEXT')).toBe('Orders');
    expect(translate(de, 'MENUITEMS.ORDERS.TEXT')).toBe('Bestellungen');
    expect(translate(es, 'MENUITEMS.EXPENSES.TEXT')).toBe('Gastos');
    expect(translate(es, 'MENUITEMS.EXPENSES.LIST.CATEGORY')).toBe('Categorías');
    expect(translate(en, 'MENUITEMS.EXPENSES.TEXT')).toBe('Expenses');
    expect(translate(de, 'MENUITEMS.EXPENSES.LIST.CATEGORY')).toBe('Kategorien');
    expect(translate(es, 'MENUITEMS.REPORTS.TEXT')).toBe('Reportes');
    expect(translate(en, 'MENUITEMS.REPORTS.TEXT')).toBe('Reports');
    expect(translate(de, 'MENUITEMS.REPORTS.TEXT')).toBe('Berichte');
  });
});
