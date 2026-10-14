import { inject } from '@angular/core';
import { Route, Router, UrlSegment } from '@angular/router';
import { APP_BASE } from './app-paths';

/**
 * Redirecciones TEMPORALES de las URLs anteriores a `/pocketbiz` (ver
 * ADR-landing-pocketbiz-rutas-compatibilidad-urls-antiguas). Retirar cuando ya no haya
 * marcadores relevantes. Solo cubre los prefijos de negocio y de autenticación; el resto de
 * rutas desconocidas llega a la página 404.
 */
const LEGACY_BUSINESS_PREFIXES: readonly string[] = [
  'dashboard',
  'catalog',
  'customers',
  'sales',
  'expenses',
  'reports',
];

/** Páginas de `/authentication/<antigua>` y su nombre actual bajo `/pocketbiz`. */
const LEGACY_AUTH_PAGES: Readonly<Record<string, string>> = {
  signin: 'login',
  signup: 'signup',
  forgot: 'forgot',
  reset: 'reset',
  page404: 'page404',
  page500: 'page500',
};

const consume = (segments: UrlSegment[]) => ({ consumed: segments });

export const LEGACY_BUSINESS_REDIRECT: Route = {
  matcher: (segments) =>
    segments.length > 0 && LEGACY_BUSINESS_PREFIXES.includes(segments[0].path)
      ? consume(segments)
      : null,
  redirectTo: ({ url, queryParams, fragment }) =>
    inject(Router).createUrlTree([APP_BASE, ...url.map((segment) => segment.path)], {
      queryParams,
      fragment: fragment ?? undefined,
    }),
};

export const LEGACY_AUTH_REDIRECT: Route = {
  matcher: (segments) =>
    segments.length === 2 &&
    segments[0].path === 'authentication' &&
    Object.prototype.hasOwnProperty.call(LEGACY_AUTH_PAGES, segments[1].path)
      ? consume(segments)
      : null,
  redirectTo: ({ url, queryParams, fragment }) =>
    inject(Router).createUrlTree([APP_BASE, LEGACY_AUTH_PAGES[url[1].path]], {
      queryParams,
      fragment: fragment ?? undefined,
    }),
};

export const LEGACY_REDIRECTS: Route[] = [LEGACY_AUTH_REDIRECT, LEGACY_BUSINESS_REDIRECT];
