import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, Router, UrlTree, provideRouter } from '@angular/router';
import { Observable, firstValueFrom } from 'rxjs';
import { environment } from '../../../environments/environment';
import { APP_PATHS } from '../routing/app-paths';
import { MODULE_DISABLED_ROUTE, moduleGuard } from './module.guard';

function route(module?: string, home = false): ActivatedRouteSnapshot {
  return { data: module ? { module, home } : {} } as unknown as ActivatedRouteSnapshot;
}

describe('moduleGuard', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    http = TestBed.inject(HttpTestingController);
  });

  const run = (module?: string, home = false) =>
    TestBed.runInInjectionContext(() => moduleGuard(route(module, home), {} as never)) as Observable<boolean | UrlTree>;

  it('lets routes without a module through', async () => {
    expect(await firstValueFrom(run())).toBeTrue();
  });

  it('allows an enabled module', async () => {
    const result = firstValueFrom(run('inventory'));
    http.expectOne(`${environment.apiUrl}/modules/`).flush([
      { key: 'inventory', name: 'Inventario', description: '', is_base: false, enabled: true, requires: [], optional: [], missing_requires: [] },
    ]);
    expect(await result).toBeTrue();
  });

  it('redirects away from a disabled module (EDGE-04)', async () => {
    const result = firstValueFrom(run('inventory'));
    http.expectOne(`${environment.apiUrl}/modules/`).flush([
      { key: 'inventory', name: 'Inventario', description: '', is_base: false, enabled: false, requires: [], optional: [], missing_requires: [] },
    ]);
    const redirect = (await result) as UrlTree;
    expect(TestBed.inject(Router).serializeUrl(redirect)).toBe(`${MODULE_DISABLED_ROUTE}?module=inventory`);
  });

  it('sends the home route to Catalog, without the error screen, when its module is disabled (AC-02)', async () => {
    const result = firstValueFrom(run('reporting', true));
    http.expectOne(`${environment.apiUrl}/modules/`).flush([
      { key: 'reporting', name: 'Reportes', description: '', is_base: false, enabled: false, requires: [], optional: [], missing_requires: [] },
    ]);
    const redirect = (await result) as UrlTree;
    expect(TestBed.inject(Router).serializeUrl(redirect)).toBe(APP_PATHS.catalog);
  });

  it('lets the home route through when its module is enabled (AC-02)', async () => {
    const result = firstValueFrom(run('reporting', true));
    http.expectOne(`${environment.apiUrl}/modules/`).flush([
      { key: 'reporting', name: 'Reportes', description: '', is_base: false, enabled: true, requires: [], optional: [], missing_requires: [] },
    ]);
    expect(await result).toBeTrue();
  });
});
