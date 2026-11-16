import { tr } from '../../../core/i18n/translate';

export const ACCOUNT_NAME_MAX_LENGTH = 80;
/** Monedas que admite una cuenta; solo `FLOW_CURRENCY` puede recibir cobros (Ventas y Cobros operan en bolivianos). */
export const CURRENCIES = ['BOB', 'USD'] as const;
export const FLOW_CURRENCY = 'BOB';

/** Dónde se mueve el dinero. No restringe si la cuenta recibe o paga. */
export const ACCOUNT_KINDS = ['CASH', 'BANK', 'WALLET'] as const;
export type AccountKind = (typeof ACCOUNT_KINDS)[number];

/** Las seis clasificaciones contables fijas, en orden de presentación (CONT-08). */
export const ACCOUNT_CLASSES = ['ASSET', 'LIABILITY', 'EQUITY', 'INCOME', 'EXPENSE', 'COST'] as const;
export type AccountClassCode = (typeof ACCOUNT_CLASSES)[number];

/** Código de cuenta: hasta 20 dígitos (por ahora solo numérico, p. ej. 111001); los espacios de los bordes se recortan. */
export const ACCOUNT_CODE_MAX_LENGTH = 20;
export const ACCOUNT_CODE_PATTERN = /^\s*\d+\s*$/;

/** Estado de una clasificación contable en la empresa: solo se habilita o deshabilita. */
export interface AccountClassState {
  code: AccountClassCode;
  enabled: boolean;
}

export interface Account {
  id: string;
  name: string;
  currency: string;
  /** `null` en cuentas anteriores a la introducción del tipo. */
  kind: AccountKind | null;
  /** Clasificación contable; `null` solo en cuentas anteriores que aún no la tienen. */
  accountClass?: AccountClassCode | null;
  /** Código del plan de cuentas (único por empresa); `null` en cuentas anteriores. */
  code?: string | null;
  /** La cuenta ya tiene asientos: su clasificación y su marca de correctora no cambian. */
  hasEntries?: boolean;
  /** Cuenta correctora: su saldo normal es contrario al de su clasificación. */
  isContra?: boolean;
  /** Monto a la fecha de corte, decimal en texto (nunca float). */
  openingBalance: string;
  isActive: boolean;
}

export interface AccountInput {
  name: string;
  currency: string;
  code?: string;
  /** Tipo de cuenta de dinero (Caja/Banco/Billetera); solo con clasificación Activo. `null` lo quita. */
  kind?: AccountKind | null;
  openingBalance?: string;
  accountClass?: AccountClassCode | null;
  isContra?: boolean;
}

export interface AccountDto {
  id: string;
  name: string;
  currency: string;
  kind?: AccountKind | null;
  account_class?: AccountClassCode | null;
  code?: string | null;
  is_contra?: boolean;
  has_entries?: boolean;
  opening_balance?: string;
  is_active: boolean;
}

export interface Gap {
  from: string;
  to: string;
}

/** Corte y cobertura de Contabilidad de la empresa. */
export interface AccountingSettings {
  cutoffDate: string | null;
  enabledAt: string | null;
  /** Hay movimientos: la fecha de corte ya no cambia. */
  locked: boolean;
  gaps: Gap[];
}

export interface AccountingSettingsDto {
  cutoff_date: string | null;
  enabled_at: string | null;
  locked: boolean;
  gaps: Gap[];
}

/** Por qué se mueve el dinero: de ingreso o de egreso. La dirección no cambia tras crearla. */
export const DIRECTIONS = ['INCOME', 'EXPENSE'] as const;
export type Direction = (typeof DIRECTIONS)[number];

export interface Classification {
  id: string;
  name: string;
  direction: Direction;
  isActive: boolean;
}

export interface ClassificationInput {
  name: string;
  direction: Direction;
}

export interface ClassificationDto {
  id: string;
  name: string;
  direction: Direction;
  is_active: boolean;
}

export interface PaymentMethod {
  code: string;
  label: string;
  isActive: boolean;
  account: Account | null;
}

export interface PaymentMethodDto {
  code: string;
  label: string;
  is_active: boolean;
  account: AccountDto | null;
}

/** Errores por campo devueltos por el servidor (clave = campo del formulario). */
export type FieldErrors = Partial<Record<string, string[]>>;

export class AccountingApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly fieldErrors: FieldErrors = {},
    /** Código estable de un 409: `account_in_use`. */
    readonly code: string | null = null,
    /** Métodos activos que bloquean la acción (códigos, 409 `account_in_use`). */
    readonly methods: string[] = [],
  ) {
    super(message);
    this.name = 'AccountingApiError';
  }
}

const FIELD_MAP: Record<string, string> = {
  name: 'name',
  currency: 'currency',
  kind: 'kind',
  direction: 'direction',
  opening_balance: 'openingBalance',
  account_class: 'accountClass',
  code: 'code',
  cutoff_date: 'cutoffDate',
  account_id: 'accountId',
  start_date: 'startDate',
  end_date: 'endDate',
};

function toFieldErrors(body: unknown): FieldErrors {
  const errors: FieldErrors = {};
  if (body && typeof body === 'object') {
    for (const [serverField, value] of Object.entries(body as Record<string, unknown>)) {
      const field = FIELD_MAP[serverField];
      if (field && Array.isArray(value)) {
        errors[field] = value.map(String);
      }
    }
  }
  return errors;
}

/** Traduce una respuesta HTTP de error a un error con mensaje listo para mostrar. */
export function toApiError(status: number, body: unknown): AccountingApiError {
  if (status === 0) {
    return new AccountingApiError(tr('CUSTOMERS.CUSTOMERS_API_SERVICE.NO_SE_PUDO_CONECTAR_CON'), 0);
  }
  if (status === 400) {
    return new AccountingApiError(tr('CUSTOMERS.CUSTOMERS_API_SERVICE.REVISA_LOS_DATOS_INGRESADOS'), 400, toFieldErrors(body));
  }
  const record = (body && typeof body === 'object' ? body : {}) as { detail?: unknown; code?: unknown; methods?: unknown };
  const detail = typeof record.detail === 'string' ? record.detail : '';
  if (status === 404) {
    return new AccountingApiError(detail || tr('EXPENSES.API_ERROR.NO_SE_ENCONTRO_EL_REGISTRO'), 404);
  }
  if (status === 409) {
    const methods = Array.isArray(record.methods) ? record.methods.map(String) : [];
    const code = typeof record.code === 'string' ? record.code : null;
    return new AccountingApiError(detail || tr('CUSTOMERS.CUSTOMERS_API_SERVICE.OCURRIO_UN_ERROR_INESPERADO_INTENTALO'), 409, {}, code, methods);
  }
  return new AccountingApiError(tr('CUSTOMERS.CUSTOMERS_API_SERVICE.OCURRIO_UN_ERROR_INESPERADO_INTENTALO'), status);
}
