import { Patient } from '../models/patient';
export function makePatient(extra: Partial<Patient> = {}): Patient {
  return {
    id: 'c-1', customer: { id: 'c-1', name: 'Ana', phone: '76543210', email: '', active: true,
      birth_date: null, responsible_name: '', responsible_phone: '' },
    active: true, created_at: '2026-11-02T14:00:00Z', updated_at: '2026-11-02T14:00:00Z', created_by: 1, updated_by: 1,
    medical_history: '', dental_history: '', allergies: '', medication: '', clinical_notes: '', ...extra,
  };
}
export const EMPTY_HISTORY = { count: 0, next: null, previous: null, results: [] };
