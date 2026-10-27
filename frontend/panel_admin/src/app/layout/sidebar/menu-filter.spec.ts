import { filterMenu } from './menu-filter';
import { RouteInfo } from './sidebar.metadata';

const base = { iconType: '', icon: '', class: '', groupTitle: false, badge: '', badgeClass: '', submenu: [] };
const item = (path: string, extra: Partial<RouteInfo> = {}): RouteInfo => ({ ...base, title: path, path, ...extra });
const paths = (items: RouteInfo[]) => items.map((entry) => entry.path);

describe('filterMenu (AC-01)', () => {
  const menu: RouteInfo[] = [
    item('/customers', { module: 'customers' }),
    item('', {
      title: 'Gastos',
      module: 'expenses',
      submenu: [item('/expenses'), item('/expenses/categories')],
    }),
    item('', { title: 'Configuración', submenu: [item('/settings/modules')] }),
    item('', {
      title: 'Mixto',
      submenu: [item('/a', { module: 'sales' }), item('/b', { module: 'inventory' })],
    }),
  ];

  it('hides items of disabled modules and keeps items without module', () => {
    expect(paths(filterMenu(menu, new Set(['expenses'])))).toEqual(['', '']);
    expect(paths(filterMenu(menu, new Set(['customers', 'expenses']))).includes('/customers')).toBeTrue();
  });

  it('children inherit the module of their group', () => {
    const result = filterMenu(menu, new Set(['expenses']));
    expect(paths(result[0].submenu)).toEqual(['/expenses', '/expenses/categories']);
    expect(filterMenu(menu, new Set()).some((entry) => entry.title === 'Gastos')).toBeFalse();
  });

  it('shows only the children whose module is enabled and drops a group with no visible children', () => {
    const only = filterMenu(menu, new Set(['inventory']));
    const mixed = only.find((entry) => entry.title === 'Mixto');
    expect(paths(mixed?.submenu ?? [])).toEqual(['/b']);
    expect(filterMenu(menu, new Set()).some((entry) => entry.title === 'Mixto')).toBeFalse();
  });

  it('keeps groups without a module (Configuración)', () => {
    expect(filterMenu(menu, new Set()).some((entry) => entry.title === 'Configuración')).toBeTrue();
  });

  it('shows only items without module while the modules are unknown', () => {
    expect(filterMenu(menu, null).map((entry) => entry.title)).toEqual(['Configuración']);
  });
});
