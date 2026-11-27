import { EncounterDetail, EncounterListItem } from '../models/encounter';

export function encounterDetail(overrides: Partial<EncounterDetail> = {}): EncounterDetail {
  return {
    appointment: {
      id: 'a1', customer_id: 'c1', customer_name: 'Ana Pérez', professional_id: 'p1', professional_name: 'Dra. Rojas',
      service_name: 'Limpieza', starts: '2030-01-07T09:00:00-04:00', ends: '2030-01-07T09:30:00-04:00', status: 'confirmed', notes: '',
    },
    is_dental: true,
    patient: { id: 'c1', name: 'Ana Pérez', phone: '+59176543210', email: '', birth_date: '1990-05-01', active: true, allergies: 'Penicilina', medical_history: 'Asma' },
    encounter: null,
    odontogram: { can_create: false, root: null, current: null },
    prescriptions_enabled: false,
    allowed_actions: ['start'],
    ...overrides,
  };
}

export function inProgress(overrides: Partial<EncounterDetail> = {}): EncounterDetail {
  return encounterDetail({
    encounter: {
      id: 'e1', status: 'in_progress', started_at: '2030-01-07T09:05:00-04:00', started_by: { id: 1, name: 'ana' },
      finished_at: null, finished_by: null, cancelled_at: null, cancelled_by: null, cancellation_reason: '', observations: '',
    },
    odontogram: { can_create: true, root: null, current: null },
    allowed_actions: ['finish', 'cancel'],
    ...overrides,
  });
}

export function listItem(overrides: Partial<EncounterListItem> = {}): EncounterListItem {
  return {
    appointment_id: 'a1b2c3d4-0000-0000-0000-000000000000', customer_id: 'c1', customer_name: 'Ana Pérez', professional_id: 'p1',
    professional_name: 'Dra. Rojas', service_name: 'Limpieza', starts: '2030-01-07T09:00:00-04:00', ends: '2030-01-07T09:30:00-04:00',
    status: 'confirmed', encounter_id: null, encounter_status: 'pending', ...overrides,
  };
}
