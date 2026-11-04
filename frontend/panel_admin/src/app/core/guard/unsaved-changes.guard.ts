import { tr } from '../i18n/translate';
import { CanDeactivateFn } from '@angular/router';

export const UNSAVED_CHANGES_MESSAGE = (): string => tr('CORE.UNSAVED_CHANGES_GUARD.HAY_CAMBIOS_SIN_GUARDAR_SALIR');

export interface HasUnsavedChanges {
  hasUnsavedChanges(): boolean;
}

/** Pide confirmación al salir de una pantalla con cambios sin guardar (comodidad de navegación, no seguridad). */
export const unsavedChangesGuard: CanDeactivateFn<HasUnsavedChanges> = (component) =>
  !component.hasUnsavedChanges() || window.confirm(UNSAVED_CHANGES_MESSAGE());
