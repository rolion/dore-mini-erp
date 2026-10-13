import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Route, Router, provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { AuthGuard } from '../guard/auth.guard';
import { APP_ROUTE } from '../../app.routes';
import { AUTH_ROUTE } from '../../authentication/auth.routes';
import { AuthLayoutComponent } from '../../layout/app-layout/auth-layout/auth-layout.component';
import { MainLayoutComponent } from '../../layout/app-layout/main-layout/main-layout.component';
import { APP_BASE, APP_PATHS } from './app-paths';
import { LEGACY_REDIRECTS } from './legacy-redirects';

@Component({ selector: 'app-dummy', template: '', standalone: true })
class DummyComponent {}

@Component({ selector: 'app-not-found', template: '', standalone: true })
class NotFoundComponent {}

const pocketbizRoute = (): Route => {
  const route = APP_ROUTE.find((r) => r.path === 'pocketbiz');
  expect(route).withContext('route "pocketbiz"').toBeDefined();
  return route as Route;
};

describe('Rutas de la aplicación (ADR landing-pocketbiz-rutas)', () => {
  describe('constantes', () => {
    it('keeps every product path under /pocketbiz', () => {
      expect(APP_BASE).toBe('/pocketbiz');
      expect(APP_PATHS.login).toBe('/pocketbiz/login');
      expect(APP_PATHS.signup).toBe('/pocketbiz/signup');
      expect(APP_PATHS.dashboard).toBe('/pocketbiz/dashboard/main');
      expect(APP_PATHS.landing).toBe('/');
    });
  });

  describe('estructura del router', () => {
    it('has no top-level "authentication" or legacy business routes outside the redirects (AC-09)', () => {
      const legacy = ['authentication', 'dashboard', 'catalog', 'customers', 'sales', 'expenses', 'reports'];
      const topLevel = APP_ROUTE.map((r) => r.path);
      for (const path of legacy) {
        expect(topLevel).not.toContain(path);
      }
    });

    it('serves login, signup, forgot, reset and the error pages without guard under /pocketbiz (AC-03)', () => {
      const children = pocketbizRoute().children ?? [];
      const authGroup = children.find((r) => r.component === AuthLayoutComponent);
      expect(authGroup).toBeDefined();
      expect(authGroup?.canActivate).toBeUndefined();

      const paths = AUTH_ROUTE.map((r) => r.path);
      expect(paths).toEqual(['login', 'signup', 'forgot', 'reset', 'page404', 'page500']);
    });

    it('protects every private route under /pocketbiz with the AuthGuard (AC-04)', () => {
      const children = pocketbizRoute().children ?? [];
      const mainGroup = children.find((r) => r.component === MainLayoutComponent);
      expect(mainGroup).toBeDefined();
      expect(mainGroup?.canActivate).toEqual([AuthGuard]);
      const privatePaths = (mainGroup?.children ?? []).map((r) => r.path);
      for (const path of ['dashboard', 'catalog/products', 'customers', 'sales/orders', 'expenses', 'reports']) {
        expect(privatePaths).toContain(path);
      }
    });

    it('sends /pocketbiz without a subroute to the dashboard (AC-05)', () => {
      const mainGroup = (pocketbizRoute().children ?? []).find((r) => r.component === MainLayoutComponent);
      const index = (mainGroup?.children ?? []).find((r) => r.path === '');
      expect(index?.redirectTo).toBe('dashboard/main');
      expect(index?.pathMatch).toBe('full');
    });

    it('ends with a 404 catch-all after the legacy redirects (EDGE-06)', () => {
      const last = APP_ROUTE[APP_ROUTE.length - 1];
      expect(last.path).toBe('**');
      expect(LEGACY_REDIRECTS.every((r) => APP_ROUTE.includes(r))).toBeTrue();
    });
  });

  describe('redirecciones de compatibilidad (AC-08)', () => {
    let router: Router;

    beforeEach(() => {
      TestBed.configureTestingModule({
        providers: [
          provideRouter([
            ...LEGACY_REDIRECTS,
            {
              matcher: (segments) =>
                segments.length > 0 && segments[0].path === 'pocketbiz' ? { consumed: segments } : null,
              component: DummyComponent,
            },
            { path: '**', component: NotFoundComponent },
          ]),
        ],
      });
      router = TestBed.inject(Router);
    });

    const cases: [string, string][] = [
      ['/authentication/signin', '/pocketbiz/login'],
      ['/authentication/signup', '/pocketbiz/signup'],
      ['/authentication/forgot', '/pocketbiz/forgot'],
      ['/authentication/reset', '/pocketbiz/reset'],
      ['/authentication/page404', '/pocketbiz/page404'],
      ['/authentication/page500', '/pocketbiz/page500'],
      ['/dashboard/main', '/pocketbiz/dashboard/main'],
      ['/catalog/products', '/pocketbiz/catalog/products'],
      ['/catalog/products/p-1/edit', '/pocketbiz/catalog/products/p-1/edit'],
      ['/customers', '/pocketbiz/customers'],
      ['/sales/orders/o-1', '/pocketbiz/sales/orders/o-1'],
      ['/expenses/categories', '/pocketbiz/expenses/categories'],
      ['/reports', '/pocketbiz/reports'],
    ];

    for (const [from, to] of cases) {
      it(`redirects ${from} to ${to}`, async () => {
        await RouterTestingHarness.create(from);
        expect(router.url).toBe(to);
      });
    }

    it('keeps the query string on the redirect (EDGE-02)', async () => {
      await RouterTestingHarness.create('/sales/orders?status=NEW');
      expect(router.url).toBe('/pocketbiz/sales/orders?status=NEW');
    });

    it('does not redirect unknown routes, they reach the 404 catch-all (AC-08)', async () => {
      await RouterTestingHarness.create('/ui/tabs');
      expect(router.url).toBe('/ui/tabs');
    });

    it('does not redirect an unknown authentication page', async () => {
      await RouterTestingHarness.create('/authentication/nope');
      expect(router.url).toBe('/authentication/nope');
    });

    it('never produces a destination that is itself a legacy origin (no cycles)', () => {
      const legacyPrefixes = ['authentication', 'dashboard', 'catalog', 'customers', 'sales', 'expenses', 'reports'];
      for (const [, to] of cases) {
        expect(to.startsWith(`${APP_BASE}/`)).toBeTrue();
        expect(legacyPrefixes).not.toContain(to.split('/')[1]);
      }
    });
  });
});
