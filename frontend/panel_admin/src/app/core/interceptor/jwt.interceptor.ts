import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { environment } from '../../../environments/environment';
import { AuthService } from '../service/auth.service';

/** Agrega `Authorization: Token <token>` a las peticiones hacia la API propia. */
export const tokenInterceptor: HttpInterceptorFn = (request, next) => {
  const token = inject(AuthService).currentUserValue?.token;
  if (token && request.url.startsWith(environment.apiUrl)) {
    request = request.clone({ setHeaders: { Authorization: `Token ${token}` } });
  }
  return next(request);
};
