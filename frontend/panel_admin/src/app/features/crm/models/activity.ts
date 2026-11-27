import { CrmOwner } from './opportunity';
import { CrmRelated } from './task';

export const CRM_ACTIVITY_NOTES_MAX_LENGTH = 2000;

export const CRM_ACTIVITY_CHANNELS = ['call', 'whatsapp', 'email', 'visit', 'other'] as const;
export type CrmActivityChannel = (typeof CRM_ACTIVITY_CHANNELS)[number];

export const CRM_ACTIVITY_OUTCOMES = ['contacted', 'no_answer', 'interested', 'not_interested', 'follow_up'] as const;
export type CrmActivityOutcome = (typeof CRM_ACTIVITY_OUTCOMES)[number];

export interface CrmActivityDto {
  id: string;
  customer_id: string | null;
  opportunity_id: string | null;
  task_id: string | null;
  actor: CrmOwner;
  channel: CrmActivityChannel;
  outcome: CrmActivityOutcome | '';
  notes: string;
  occurred_at: string;
  created_at: string;
}

export interface CrmActivityPageDto {
  count: number;
  next: string | null;
  previous: string | null;
  results: CrmActivityDto[];
}

export interface CrmActivity {
  id: string;
  customerId: string | null;
  opportunityId: string | null;
  taskId: string | null;
  actor: CrmOwner;
  channel: CrmActivityChannel;
  outcome: CrmActivityOutcome | '';
  notes: string;
  occurredAt: string;
  createdAt: string;
}

export interface CrmActivityPage {
  count: number;
  results: CrmActivity[];
}

/** Datos de una actividad; sin `occurredAt` el servidor usa «ahora». */
export interface CrmActivityDetails {
  channel: CrmActivityChannel;
  outcome: CrmActivityOutcome | '';
  notes: string;
  /** ISO 8601 en UTC. */
  occurredAt?: string;
}

export interface CrmActivityInput extends CrmActivityDetails {
  related: Pick<CrmRelated, 'type' | 'id'>;
}
