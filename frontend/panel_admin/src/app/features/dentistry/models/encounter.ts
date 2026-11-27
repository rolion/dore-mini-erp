import { tr } from '../../../core/i18n/translate';

export type EncounterStatus = 'pending' | 'in_progress' | 'finished' | 'cancelled';
export type EncounterAction = 'start' | 'finish' | 'cancel';
export type AppointmentStatusValue = 'scheduled' | 'confirmed' | 'cancelled' | 'attended' | 'no_show';

export const ENCOUNTER_STATUSES: EncounterStatus[] = ['pending', 'in_progress', 'finished', 'cancelled'];

/** Badges con fondo suave y texto de énfasis de Bootstrap: contraste AA en tema claro y oscuro (siempre con texto). */
export function appointmentTone(status: AppointmentStatusValue): string {
  const tone = { scheduled: 'warning', confirmed: 'primary', cancelled: 'danger', attended: 'success', no_show: 'secondary' }[status];
  return `bg-${tone}-subtle text-${tone}-emphasis`;
}

export function encounterTone(status: EncounterStatus): string {
  const tone = { pending: 'warning', in_progress: 'primary', finished: 'success', cancelled: 'danger' }[status];
  return `bg-${tone}-subtle text-${tone}-emphasis`;
}

export const CANCEL_REASON_MAX = 500;
export const OBSERVATIONS_MAX = 2000;

/** Etiqueta del estado de la atención en el idioma activo; se evalúa al renderizar, nunca en una constante. */
export function encounterStatusLabel(status: EncounterStatus): string {
  return tr(`DENTISTRY.ENCOUNTER.ESTADO_${status.toUpperCase()}`);
}

export interface EncounterListItem {
  appointment_id: string;
  customer_id: string;
  customer_name: string;
  professional_id: string;
  professional_name: string;
  service_name: string;
  starts: string;
  ends: string;
  status: AppointmentStatusValue;
  encounter_id: string | null;
  encounter_status: EncounterStatus;
}

export interface EncounterFilters {
  from: string;
  to: string;
  professional: string;
  search: string;
  status: AppointmentStatusValue | '';
  encounter_status: EncounterStatus | '';
  page: number;
}

export interface EncounterList {
  count: number;
  results: EncounterListItem[];
  from: string;
  to: string;
}

export interface ActorRef { id: number; name: string }

export interface Encounter {
  id: string;
  status: Exclude<EncounterStatus, 'pending'>;
  started_at: string;
  started_by: ActorRef;
  finished_at: string | null;
  finished_by: ActorRef | null;
  cancelled_at: string | null;
  cancelled_by: ActorRef | null;
  cancellation_reason: string;
  observations: string;
}

export interface EncounterPatient {
  id: string;
  name: string;
  phone: string;
  email: string;
  birth_date: string | null;
  active: boolean;
  medical_history?: string;
  dental_history?: string;
  allergies?: string;
  medication?: string;
}

export interface EncounterOdontogramRef { id: string; sequence: number; status: 'draft' | 'confirmed' }

export interface EncounterOdontogram {
  can_create: boolean;
  root: EncounterOdontogramRef | null;
  current: EncounterOdontogramRef | null;
  versions?: number;
}

export interface EncounterDetail {
  appointment: {
    id: string; customer_id: string; customer_name: string; professional_id: string; professional_name: string;
    service_name: string; starts: string; ends: string; status: AppointmentStatusValue; notes: string;
  };
  is_dental: boolean;
  patient: EncounterPatient;
  encounter: Encounter | null;
  odontogram: EncounterOdontogram;
  prescriptions_enabled: boolean;
  allowed_actions: EncounterAction[];
}

export interface PatientEncounter {
  id: string;
  appointment_id: string;
  status: Exclude<EncounterStatus, 'pending'>;
  started_at: string;
  finished_at: string | null;
  professional_name: string;
  service_name: string;
  has_odontogram: boolean;
}

export interface EncounterFailure { message: string; code: string; status: number }
