export type SettingKind = 'choice' | 'percent' | 'boolean';

export interface SettingChoice {
  value: string;
  label: string;
}

/** Ajuste de un módulo con su valor actual (`value`) y el inicial documentado (`default`). */
export interface Setting {
  key: string;
  label: string;
  description: string;
  kind: SettingKind;
  value: string;
  default: string;
  choices: SettingChoice[];
  minimum: string | null;
  maximum: string | null;
}

export interface ModuleSettings {
  module: string;
  settings: Setting[];
}

export interface SettingChange {
  id: string;
  changedAt: string;
  changedBy: string;
  settingKey: string;
  settingLabel: string;
  oldValue: string;
  newValue: string;
}

export interface SettingOption {
  key: string;
  label: string;
}

export interface SettingHistoryPage {
  count: number;
  results: SettingChange[];
  settings: SettingOption[];
}

export interface HistoryFilters {
  dateFrom: string;
  dateTo: string;
  setting: string;
  page: number;
}

export const HISTORY_PAGE_SIZE = 20;

export const SETTINGS_ERROR_MESSAGE = 'No se pudo completar la operación. Inténtalo de nuevo.';

/** Error de la API de ajustes: mensaje general y errores por clave de ajuste (400). */
export class SettingsApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly fieldErrors: Record<string, string> = {},
  ) {
    super(message);
    this.name = 'SettingsApiError';
  }
}
