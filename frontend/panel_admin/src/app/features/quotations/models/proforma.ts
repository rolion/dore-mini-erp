import { tr } from '../../../core/i18n/translate';
import { AcceptanceStatus, LineDecisionFields, ProformaDecisionState } from '../../../shared/models/proforma-decisions';

export type ProformaStatus = 'draft' | 'presented' | 'superseded';
export type ProformaAction = 'edit' | 'present' | 'new-version';

export const STATUSES: ProformaStatus[] = ['draft', 'presented', 'superseded'];

/** Se evalúa al usarla (no en una constante de módulo): el catálogo se carga al arrancar. */
export function statusLabel(status: ProformaStatus): string {
  return tr(`QUOTATIONS.PROFORMAS.ESTADO_${status.toUpperCase()}`);
}

export const STATUS_CLASSES: Record<ProformaStatus, string> = {
  draft: 'col-orange',
  presented: 'col-blue',
  superseded: 'col-grey',
};

export const NOTES_MAX_LENGTH = 2000;

export interface ProformaLine extends LineDecisionFields {
  id: string;
  service_id: string;
  description: string;
  quantity: string;
  unit_price: string;
  subtotal: string;
  treatment_item_id: string | null;
  piece: string;
}

export interface ProformaSummary {
  id: string;
  number: string;
  version: number;
  status: ProformaStatus;
  customer_id: string;
  customer_name: string;
  date: string;
  valid_until: string | null;
  currency: string;
  total: string;
  accepted_total: string;
  acceptance_status: AcceptanceStatus;
  /** Presentada y con líneas aceptadas: se puede cobrar (PB-COB-001). */
  collectible?: boolean;
}

export interface Proforma extends ProformaSummary, ProformaDecisionState {
  notes: string;
  lines: ProformaLine[];
  allowed_actions: ProformaAction[];
  can_edit_price: boolean;
  versions: ProformaSummary[];
}

/** Línea que se envía: el servidor ignora descripción, subtotal y total, y los recalcula. */
export interface ProformaLineInput {
  id?: string;
  service_id?: string;
  quantity: string;
  unit_price?: string;
}

export interface ProformaInput {
  customer_id: string;
  date: string;
  valid_until: string | null;
  notes: string;
  lines: ProformaLineInput[];
}

export interface ProformaFilters {
  customer?: string;
  from?: string;
  to?: string;
  status?: ProformaStatus | '';
  page?: number;
}

export interface ProformaFailure {
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
