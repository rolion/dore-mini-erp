import { inject } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivateFn, Router, UrlTree } from '@angular/router';
import { Observable, filter, map, of, take } from 'rxjs';
import { ModulesService } from '../service/modules.service';

/** Destino cuando el módulo de la ruta no está habilitado: Catálogo es base y siempre está disponible. */
export const MODULE_DISABLED_REDIRECT = '/catalog/products';

/**
 * Deja pasar la ruta solo si su módulo (`data.module`) está habilitado para la empresa. Es una comodidad de
 * navegación, no seguridad: el bloqueo en la API llega con PB-MOD-004.
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
    map((keys) => (keys.has(key) ? true : router.createUrlTree([MODULE_DISABLED_REDIRECT]))),
  );
};
