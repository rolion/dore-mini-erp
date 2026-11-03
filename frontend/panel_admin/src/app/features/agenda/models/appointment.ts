export type AppointmentStatus = 'scheduled' | 'confirmed' | 'cancelled' | 'attended' | 'no_show';
export type AppointmentAction = 'confirm' | 'reschedule' | 'cancel' | 'attend' | 'no_show';

export const STATUS_LABELS: Record<AppointmentStatus, string> = {
  scheduled: 'Programada',
  confirmed: 'Confirmada',
  cancelled: 'Cancelada',
  attended: 'Atendida',
  no_show: 'No asistió',
};

export const STATUS_CLASSES: Record<AppointmentStatus, string> = {
  scheduled: 'col-orange',
  confirmed: 'col-blue',
  cancelled: 'col-red',
  attended: 'col-green',
  no_show: 'col-grey',
};

export const EVENT_LABELS: Record<string, string> = {
  created: 'Creada',
  confirmed: 'Confirmada',
  rescheduled: 'Reprogramada',
  cancelled: 'Cancelada',
  attended: 'Atendida',
  no_show: 'No asistió',
};

export const REASON_MAX_LENGTH = 500;
export const NOTES_MAX_LENGTH = 1000;

export interface AppointmentEvent {
  id: number;
  kind: string;
  author_id: number;
  created_at: string;
  reason: string;
  previous_starts: string | null;
  previous_ends: string | null;
}

export interface Appointment {
  id: string;
  professional_id: string;
  professional_name: string;
  customer_id: string;
  customer_name: string;
  service_id: string;
  service_name: string;
  starts: string;
  ends: string;
  duration_minutes: number;
  notes: string;
  status: AppointmentStatus;
  allowed_actions: AppointmentAction[];
  timezone: string;
  created_at?: string;
  history?: AppointmentEvent[];
}

export interface AppointmentFilters {
  from?: string;
  to?: string;
  professional?: string;
  status?: AppointmentStatus | '';
  search?: string;
  page?: number;
  page_size?: number;
}

export interface AppointmentInput {
  professional_id: string;
  customer_id: string;
  service_id: string;
  starts: string;
  duration_minutes: number;
  notes: string;
}

export interface Slot { starts: string; ends: string }

export interface FreeSlots { timezone: string; slots: Slot[]; now: string }

export interface AppointmentFailure {
  message: string;
  fields: Record<string, string>;
  conflict: boolean;
}
