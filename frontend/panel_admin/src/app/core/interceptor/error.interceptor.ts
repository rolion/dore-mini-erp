import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuthService } from '../service/auth.service';

const LOGIN_URL = `${environment.apiUrl}/auth/login/`;

/** Ante un 401 fuera del login, la sesión ya no es válida: se limpia y se vuelve al login. */
export const errorInterceptor: HttpInterceptorFn = (request, next) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  return next(request).pipe(
    catchError((err: HttpErrorResponse) => {
      if (err.status === 401 && request.url !== LOGIN_URL) {
        authService.clearSession();
        router.navigate(['/authentication/signin']);
      }
      return throwError(() => err);
    })
  );
};
