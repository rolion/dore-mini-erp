/** Clasificación de egreso asociada, tal como la devuelve la API. */
export interface ClassificationRef {
  id: string;
  name: string;
  active: boolean;
}

/** Categoría de Gastos con su clasificación de egreso (o `null` si falta configurarla). */
export interface CategoryConfig {
  id: string;
  name: string;
  classification: ClassificationRef | null;
}

export interface CategoryConfigDto {
  id: string;
  name: string;
  classification: ClassificationRef | null;
}

export interface PaymentClassificationDto {
  classification: ClassificationRef | null;
}

/** Estado de una fila de configuración. */
export type ConfigStatus = 'configured' | 'pending' | 'inactive';

export function configStatus(classification: ClassificationRef | null): ConfigStatus {
  if (classification === null) {
    return 'pending';
  }
  return classification.active ? 'configured' : 'inactive';
}

/** Error de la API de configuración con el primer mensaje legible. */
export class ExpenseConfigError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = 'ExpenseConfigError';
  }
}
