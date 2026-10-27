import { inject } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivateFn, Router, UrlTree } from '@angular/router';
import { Observable, filter, map, of, take } from 'rxjs';
import { APP_PATHS } from '../routing/app-paths';
import { ModulesService } from '../service/modules.service';

/** Pantalla «Módulo no habilitado» a la que lleva una ruta de un módulo deshabilitado. */
export const MODULE_DISABLED_ROUTE = APP_PATHS.moduleDisabled;

/**
 * Deja pasar la ruta solo si su módulo (`data.module`) está habilitado para la empresa. Es una comodidad de
 * navegación; el bloqueo real lo hace la API (403 `module_disabled`). La ruta con `data.home` es la página
 * inicial: si su módulo no está habilitado redirige a Catálogo (base) sin pantalla de error.
 */
export const moduleGuard: CanActivateFn = (route: ActivatedRouteSnapshot): Observable<boolean | UrlTree> => {
  const key = route.data['module'] as string | undefined;
  if (!key) {
    return of(true);
  }
  const modules = inject(ModulesService);
  const router = inject(Router);
  if (modules.enabledKeysValue === null) {
    modules.loadQuietly().subscribe();
  }
  return modules.enabledKeys$.pipe(
    filter((keys): keys is ReadonlySet<string> => keys !== null),
    take(1),
    map((keys) => {
      if (keys.has(key)) {
        return true;
      }
      return route.data['home'] === true
        ? router.createUrlTree([APP_PATHS.catalog])
        : router.createUrlTree([MODULE_DISABLED_ROUTE], { queryParams: { module: key } });
    }),
  );
};
