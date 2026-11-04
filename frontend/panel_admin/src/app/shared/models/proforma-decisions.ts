import { tr } from '../../core/i18n/translate';

/** Tipos comunes de las decisiones del paciente sobre las líneas de una proforma (Cotizaciones y Odontología). */
export type LineDecision = 'pending' | 'accepted' | 'rejected';
export type AcceptanceStatus = 'pending' | 'partially_accepted' | 'accepted' | 'rejected';
export type LineKind = 'original' | 'carried' | 'replacement' | 'additional';
export type DecisionAction = 'decide' | 'rectify';
export type AcceptanceMedium = 'in_person' | 'phone' | 'message' | 'email' | 'signed_document' | 'other';

export const ACCEPTANCE_MEDIA: AcceptanceMedium[] = ['in_person', 'phone', 'message', 'email', 'signed_document', 'other'];
export const DECISION_NAME_MAX = 120;
export const DECISION_REFERENCE_MAX = 200;
export const DECISION_REASON_MAX = 500;

export interface DecisionDetail {
  id: string;
  kind: 'decision' | 'rectification' | 'carried';
  decision: Exclude<LineDecision, 'pending'>;
  decided_at: string;
  recorded_by_name: string;
  accepted_by_name: string;
  medium: AcceptanceMedium | '';
  reference: string;
  reason: string;
}

export interface DecisionHistoryItem extends DecisionDetail {
  line_id: string;
  line_description: string;
}

export interface ProformaTotals {
  proposed: string;
  accepted: string;
  pending: string;
  rejected: string;
}

/** Campos de decisión que el servidor añade a cada línea. */
export interface LineDecisionFields {
  line_kind: LineKind;
  origin_line_id: string | null;
  decision: LineDecision;
  decided_at: string | null;
  decision_detail: DecisionDetail | null;
  authorized: boolean;
}

/** Campos de decisión que el servidor añade al detalle de la proforma. */
export interface ProformaDecisionState {
  decision_actions: DecisionAction[];
  totals: ProformaTotals;
  decision_history: DecisionHistoryItem[];
  previous_version_id: string | null;
  acceptance_status: AcceptanceStatus;
}

export interface DecisionLineView extends Partial<LineDecisionFields> {
  id: string;
  description: string;
  quantity: string;
  unit_price: string;
  subtotal: string;
  /** Pieza dental (Odontología) o referencia de pieza (Cotizaciones); vacío si no aplica. */
  piece?: string;
}

/** Cuerpo de «Registrar decisión» y «Rectificar». */
export interface DecisionBody {
  idempotency_key: string;
  decision: 'accepted' | 'rejected';
  line_ids?: string[];
  accepted_by_name: string;
  medium: AcceptanceMedium | '';
  reference: string;
  reason: string;
}

export interface DecisionResult extends ProformaDecisionState {
  id: string;
  replayed: boolean;
  summary?: { lines: number; amount: string };
}

export interface DecisionFailure {
  message: string;
  fields: Record<string, string>;
  conflict: boolean;
}

/** Vista imprimible: solo datos comerciales que el servidor decide exponer. */
export interface PrintableProforma {
  number: string;
  version: number;
  status: string;
  customer_name?: string;
  patient_name?: string;
  date: string;
  valid_until: string | null;
  currency: string;
  notes: string;
  acceptance_status: AcceptanceStatus;
  totals: Omit<ProformaTotals, 'rejected'>;
  lines: {
    description: string;
    piece?: string;
    dental_piece?: string;
    quantity: string;
    unit_price: string;
    subtotal: string;
    decision: LineDecision;
    decided_at: string | null;
  }[];
}

/** Se evalúan al usarlas (no en constantes de módulo): el catálogo se carga al arrancar. */
export function decisionLabel(decision: LineDecision): string {
  return tr(`PROFORMA_DECISIONS.DECISION_${decision.toUpperCase()}`);
}

export function acceptanceLabel(status: AcceptanceStatus): string {
  return tr(`PROFORMA_DECISIONS.ACEPTACION_${status.toUpperCase()}`);
}

export function mediumLabel(medium: AcceptanceMedium | ''): string {
  return medium ? tr(`PROFORMA_DECISIONS.MEDIO_${medium.toUpperCase()}`) : '—';
}

export function lineKindLabel(kind: LineKind): string {
  return tr(`PROFORMA_DECISIONS.TIPO_${kind.toUpperCase()}`);
}

export const DECISION_CLASSES: Record<LineDecision, string> = {
  pending: 'col-grey',
  accepted: 'col-green',
  rejected: 'col-red',
};

export const ACCEPTANCE_CLASSES: Record<AcceptanceStatus, string> = {
  pending: 'col-grey',
  partially_accepted: 'col-blue',
  accepted: 'col-green',
  rejected: 'col-red',
};
