import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, Router, UrlTree, provideRouter } from '@angular/router';
import { Observable, firstValueFrom } from 'rxjs';
import { environment } from '../../../environments/environment';
import { MODULE_DISABLED_ROUTE, moduleGuard } from './module.guard';

function route(module?: string): ActivatedRouteSnapshot {
  return { data: module ? { module } : {} } as unknown as ActivatedRouteSnapshot;
}

describe('moduleGuard', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    http = TestBed.inject(HttpTestingController);
  });

  const run = (module?: string) =>
    TestBed.runInInjectionContext(() => moduleGuard(route(module), {} as never)) as Observable<boolean | UrlTree>;

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
});
