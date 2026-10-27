/**
 * Compatibilidad TEMPORAL con las URLs con hash (`/#/authentication/signin`) que la aplicación
 * usaba antes de pasar a URLs limpias (ADR-landing-pocketbiz-rutas-url-sin-hash).
 *
 * Se ejecuta antes de arrancar Angular: convierte `/#/<ruta>` en `/<ruta>` con `replaceState`
 * y las redirecciones de `legacy-redirects.ts` resuelven la ruta antigua. Retirar junto con ellas.
 */

/** Ruta interna del hash (`#/a/b?x=1` → `/a/b?x=1`), o `null` si el hash no es una ruta. */
export function legacyHashTarget(hash: string): string | null {
  return hash.startsWith('#/') && hash.length > 2 ? hash.slice(1) : null;
}

/** Reemplaza la entrada del historial por la ruta limpia. Devuelve `true` si reescribió la URL. */
export function redirectLegacyHash(win: Pick<Window, 'location' | 'history'>): boolean {
  const target = legacyHashTarget(win.location.hash);
  if (target === null) {
    return false;
  }
  win.history.replaceState(null, '', target);
  return true;
}
