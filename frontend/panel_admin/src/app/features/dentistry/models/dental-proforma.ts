import { tr } from '../../../core/i18n/translate';

export type DentalProformaStatus = 'draft' | 'presented' | 'superseded';
export type DentalProformaAction = 'edit' | 'present' | 'new-version';

export const PROFORMA_STATUSES: DentalProformaStatus[] = ['draft', 'presented', 'superseded'];

/** Se evalúa al usarla (no en una constante de módulo): el catálogo se carga al arrancar. */
export function proformaStatusLabel(status: DentalProformaStatus): string {
  return tr(`DENTISTRY.PROFORMAS.ESTADO_${status.toUpperCase()}`);
}

export const PROFORMA_STATUS_CLASSES: Record<DentalProformaStatus, string> = {
  draft: 'col-orange',
  presented: 'col-blue',
  superseded: 'col-grey',
};

export const PROFORMA_NOTES_MAX_LENGTH = 2000;
export const DENTAL_PIECE_MAX_LENGTH = 20;

export interface DentalProformaLine {
  id: string;
  service_id: string;
  description: string;
  quantity: string;
  unit_price: string;
  subtotal: string;
  dental_piece: string;
}

export interface DentalProformaSummary {
  id: string;
  number: string;
  version: number;
  status: DentalProformaStatus;
  customer_id: string;
  patient_name: string;
  date: string;
  valid_until: string | null;
  currency: string;
  total: string;
}

export interface DentalProforma extends DentalProformaSummary {
  notes: string;
  lines: DentalProformaLine[];
  allowed_actions: DentalProformaAction[];
  can_edit_price: boolean;
  versions: DentalProformaSummary[];
}

/** Línea que se envía: el servidor ignora descripción, subtotal y total, y los recalcula. */
export interface DentalProformaLineInput {
  id?: string;
  service_id?: string;
  quantity: string;
  unit_price?: string;
  dental_piece: string;
}

export interface DentalProformaInput {
  date: string;
  valid_until: string | null;
  notes: string;
  lines: DentalProformaLineInput[];
}

export interface DentalProformaFailure {
  message: string;
  fields: Record<string, string>;
  /** Mensaje por posición de línea (vacío si la línea es válida). */
  lines: Record<string, string>[];
  conflict: boolean;
}

/** Subtotal con dos decimales, redondeo half-up; solo vista previa (el servidor es la autoridad). */
export function previewSubtotal(quantity: string, unitPrice: string): number {
  const cents = Math.round(Number(quantity) * Number(unitPrice) * 100 + 1e-9);
  return Number.isFinite(cents) ? cents / 100 : 0;
}
