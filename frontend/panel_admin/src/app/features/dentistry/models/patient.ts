import { tr } from '../../../core/i18n/translate';
export const CLINICAL_FIELDS = [
  { key: 'medical_history', get label() { return tr('DENTISTRY.PATIENT.ANTECEDENTES_MEDICOS'); } },
  { key: 'dental_history', get label() { return tr('DENTISTRY.PATIENT.ANTECEDENTES_ODONTOLOGICOS'); } },
  { key: 'allergies', get label() { return tr('DENTISTRY.PATIENT.ALERGIAS'); } },
  { key: 'medication', get label() { return tr('DENTISTRY.PATIENT.MEDICACION'); } },
  { key: 'clinical_notes', get label() { return tr('DENTISTRY.PATIENT.OBSERVACIONES_CLINICAS'); } },
] as const;
export type ClinicalField = typeof CLINICAL_FIELDS[number]['key'];
export type ClinicalInput = Record<ClinicalField, string>;
export interface Demographics {
  birth_date: string | null;
  responsible_name: string;
  responsible_phone: string;
}
export interface PatientSummary {
  id: string;
  customer: Demographics & { id: string; name: string; phone: string; email: string; active: boolean };
  active: boolean;
  created_at: string;
  updated_at: string;
  created_by: number;
  updated_by: number;
}
export type Patient = PatientSummary & ClinicalInput;
export interface PatientHistory {
  id: number;
  author_id: number;
  author_name: string;
  action?: string;
  created_at: string;
  before: Record<string, string | boolean | null>;
  after: Record<string, string | boolean | null>;
}
