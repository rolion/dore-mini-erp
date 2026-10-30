import { Route } from '@angular/router';

import { APP_ROUTE } from '../../app.routes';
import { PURCHASES_ROUTE } from './purchases.routes';

function privateRoutes(): Route[] {
  const pocketbiz = APP_ROUTE.find((r) => r.path === 'pocketbiz');
  const main = (pocketbiz?.children ?? []).find((r) => (r.children ?? []).some((c) => c.path === 'purchases'));
  return main?.children ?? [];
}

describe('rutas de Compras (AC-12)', () => {
  it('declares purchases/suppliers and purchases/settings before purchases, so they are not read as an id', () => {
    const paths = privateRoutes().map((r) => r.path);
    const purchases = paths.indexOf('purchases');
    expect(purchases).toBeGreaterThan(-1);
    expect(paths.indexOf('purchases/suppliers')).toBeGreaterThan(-1);
    expect(paths.indexOf('purchases/suppliers')).toBeLessThan(purchases);
    expect(paths.indexOf('purchases/settings')).toBeLessThan(purchases);
  });

  it('guards the purchases route with the module guard of Compras', () => {
    const route = privateRoutes().find((r) => r.path === 'purchases');
    expect(route?.data?.['module']).toBe('purchases');
    expect(route?.canActivate?.length).toBe(1);
  });

  it('puts new and :id/edit before :id', () => {
    const paths = PURCHASES_ROUTE.map((r) => r.path);
    expect(paths).toEqual(['', 'new', ':id/edit', ':id/receipts/new', ':id/receipts/:receiptId', ':id']);
  });

  it('asks for confirmation when leaving the form with unsaved changes', () => {
    const forms = PURCHASES_ROUTE.filter((r) => ['new', ':id/edit', ':id/receipts/new'].includes(r.path ?? ''));
    expect(forms.every((r) => r.canDeactivate?.length === 1)).toBeTrue();
  });
});
