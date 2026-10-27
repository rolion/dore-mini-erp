import { CanDeactivateFn } from '@angular/router';

export const UNSAVED_CHANGES_MESSAGE = 'Hay cambios sin guardar. ¿Salir sin guardar?';

export interface HasUnsavedChanges {
  hasUnsavedChanges(): boolean;
}

/** Pide confirmación al salir de una pantalla con cambios sin guardar (comodidad de navegación, no seguridad). */
export const unsavedChangesGuard: CanDeactivateFn<HasUnsavedChanges> = (component) =>
  !component.hasUnsavedChanges() || window.confirm(UNSAVED_CHANGES_MESSAGE);
