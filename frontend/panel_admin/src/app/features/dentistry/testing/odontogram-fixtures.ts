import { Evaluation, OdontogramCatalog } from '../models/odontogram';

const range = (tens: number[], from: number, to: number): number[] =>
  tens.flatMap(ten => Array.from({ length: to - from + 1 }, (_, i) => ten * 10 + from + i));

export function makeCatalog(): OdontogramCatalog {
  return {
    catalog_version: 1,
    pending_clinical_validation: true,
    dentitions: [{ code: 'permanent', name: 'Permanente' }, { code: 'temporary', name: 'Temporal' }, { code: 'mixed', name: 'Mixta' }],
    surfaces: [{ code: 'M', name: 'Mesial' }, { code: 'D', name: 'Distal' }, { code: 'V', name: 'Vestibular' }, { code: 'O', name: 'Oclusal' },
      { code: 'I', name: 'Incisal' }, { code: 'P', name: 'Palatina' }, { code: 'L', name: 'Lingual' }],
    conditions: [
      { code: 'healthy', name: 'Sano', abbr: 'SAN', color: 'success', scope: 'whole', requires_note: false },
      { code: 'caries', name: 'Caries', abbr: 'CAR', color: 'danger', scope: 'surfaces', requires_note: false },
      { code: 'filling', name: 'Obturación', abbr: 'OBT', color: 'info', scope: 'surfaces', requires_note: false },
      { code: 'crown', name: 'Corona', abbr: 'COR', color: 'warning', scope: 'whole', requires_note: false },
      { code: 'other', name: 'Otro', abbr: 'OTR', color: 'light', scope: 'either', requires_note: true },
    ],
    teeth: { permanent: range([1, 2, 3, 4], 1, 8), temporary: range([5, 6, 7, 8], 1, 5) },
  };
}

export function makeEvaluation(extra: Partial<Evaluation> = {}): Evaluation {
  return {
    id: 'e-1', customer_id: 'c-1', sequence: 1, status: 'draft', dentition: 'mixed', clinical_date: '2026-11-20',
    professional: null, author: { id: 1, name: 'admin' }, created_at: '2026-11-20T10:00:00Z', confirmed_at: null, confirmed_by: null,
    amends_id: null, amends_sequence: null, amendment_reason: '', replaced_by_id: null, replaced_by_sequence: null, catalog_version: 1,
    findings: [], general_findings: [], allowed_actions: ['edit', 'confirm', 'discard'], ...extra,
  };
}
