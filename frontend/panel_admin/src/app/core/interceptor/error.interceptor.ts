import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import { MODULE_DISABLED_ROUTE } from '../guard/module.guard';
import { AuthService } from '../service/auth.service';
import { APP_PATHS } from '../routing/app-paths';
import { ModulesService } from '../service/modules.service';

const LOGIN_URL = `${environment.apiUrl}/auth/login/`;

interface ModuleDisabledBody {
  code?: unknown;
  module?: unknown;
}

function disabledModule(err: HttpErrorResponse): string | null {
  const body = (err.error && typeof err.error === 'object' ? err.error : {}) as ModuleDisabledBody;
  return err.status === 403 && body.code === 'module_disabled' && typeof body.module === 'string' ? body.module : null;
}

/**
 * Ante un 401 fuera del login, la sesión ya no es válida: se limpia y se vuelve al login. Ante un 403
 * `module_disabled` se refresca el menú y se muestra «Módulo no habilitado» (el error se propaga igualmente).
 */
export const errorInterceptor: HttpInterceptorFn = (request, next) => {
  const authService = inject(AuthService);
  const router = inject(Router);
  const modules = inject(ModulesService);

  return next(request).pipe(
    catchError((err: HttpErrorResponse) => {
      if (err.status === 401 && request.url !== LOGIN_URL) {
        authService.clearSession();
        router.navigate([APP_PATHS.login]);
      }
      const module = disabledModule(err);
      if (module !== null) {
        modules.loadQuietly().subscribe();
        router.navigate([MODULE_DISABLED_ROUTE], { queryParams: { module } });
      }
      return throwError(() => err);
    })
  );
};
