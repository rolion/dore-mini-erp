export type Dentition = 'permanent' | 'temporary' | 'mixed';
export type SurfaceCode = 'M' | 'D' | 'V' | 'O' | 'I' | 'P' | 'L';
export type ConditionScope = 'whole' | 'surfaces' | 'either';
export type EvaluationStatus = 'draft' | 'confirmed';
/** Acciones que el servidor permite sobre una evaluación; el frontend no es la barrera de seguridad. */
export type EvaluationAction = 'edit' | 'confirm' | 'amend' | 'discard';

export interface OdontogramCondition {
  code: string;
  name: string;
  abbr: string;
  /** Color de estado de Bootstrap (success, danger, info, warning, secondary, primary, dark, light…). */
  color: string;
  scope: ConditionScope;
  requires_note: boolean;
}

export interface OdontogramCatalog {
  catalog_version: string | number;
  pending_clinical_validation: boolean;
  dentitions: { code: Dentition; name: string }[];
  surfaces: { code: SurfaceCode; name: string }[];
  conditions: OdontogramCondition[];
  teeth: { permanent: number[]; temporary: number[] };
}

export interface Finding {
  id?: string;
  piece: number;
  surfaces: SurfaceCode[];
  condition: string;
  diagnosis: string;
  notes: string;
}

export interface GeneralFinding {
  id?: string;
  diagnosis: string;
  notes: string;
}

export interface Evaluation {
  id: string;
  customer_id: string;
  sequence: number;
  status: EvaluationStatus;
  dentition: Dentition;
  clinical_date: string;
  professional: { id: string; name: string } | null;
  author: { id: number; name: string };
  created_at: string;
  confirmed_at: string | null;
  confirmed_by: { id: number; name: string } | null;
  amends_id: string | null;
  amends_sequence: number | null;
  amendment_reason: string;
  replaced_by_id: string | null;
  replaced_by_sequence: number | null;
  catalog_version: string | number;
  findings: Finding[];
  general_findings: GeneralFinding[];
  allowed_actions: EvaluationAction[];
}

export interface EvaluationInput {
  dentition: Dentition;
  clinical_date: string;
  professional_id: string | null;
  findings: Finding[];
  general_findings: GeneralFinding[];
}

export type PieceKind = 'incisor' | 'canine' | 'premolar' | 'molar';

export const DEFAULT_CATALOG_CONDITION_COLOR = 'secondary';
export const DIAGNOSIS_MAX = 500;
export const NOTES_MAX = 1000;
export const REASON_MAX = 500;
