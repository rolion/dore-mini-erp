/**
 * Rutas absolutas del producto. La aplicación vive bajo `/pocketbiz`; la raíz `/` es la
 * landing pública (ver ADR-landing-pocketbiz-rutas-esquema-rutas-montaje).
 */
export const APP_BASE = '/pocketbiz';

export const APP_PATHS = {
  landing: '/',
  login: `${APP_BASE}/login`,
  signup: `${APP_BASE}/signup`,
  dashboard: `${APP_BASE}/dashboard/main`,
  catalog: `${APP_BASE}/catalog/products`,
  moduleDisabled: `${APP_BASE}/module-disabled`,
} as const;
