import { CrmOwner } from './opportunity';

export const CRM_TASK_TITLE_MAX_LENGTH = 150;

export type CrmTaskStatus = 'pending' | 'done' | 'cancelled' | 'archived';
/** Valores del filtro `status` de la API; las archivadas nunca se listan. */
export type CrmTaskFilter = 'pending' | 'overdue' | 'done' | 'cancelled' | 'all';
export type CrmRelatedType = 'customer' | 'opportunity';

/** Entidad a la que se refiere una tarea o actividad: un cliente o una oportunidad. */
export interface CrmRelated {
  type: CrmRelatedType;
  id: string;
  name: string;
}

export interface CrmTaskDto {
  id: string;
  title: string;
  related: CrmRelated;
  owner: CrmOwner;
  due_at: string;
  status: CrmTaskStatus;
  is_overdue: boolean;
  completed_at: string | null;
  created_at: string;
}

export interface CrmTaskPageDto {
  count: number;
  next: string | null;
  previous: string | null;
  results: CrmTaskDto[];
}

export interface CrmTask {
  id: string;
  title: string;
  related: CrmRelated;
  owner: CrmOwner;
  dueAt: string;
  status: CrmTaskStatus;
  isOverdue: boolean;
  completedAt: string | null;
  createdAt: string;
}

export interface CrmTaskPage {
  count: number;
  results: CrmTask[];
}

export interface CrmTaskListParams {
  ownerId?: number;
  status?: CrmTaskFilter;
  customerId?: string;
  opportunityId?: string;
  page?: number;
  pageSize?: number;
}

export interface CrmTaskInput {
  title: string;
  /** ISO 8601 en UTC. */
  dueAt: string;
  related: Pick<CrmRelated, 'type' | 'id'>;
  ownerId?: number;
}

export interface CrmTaskUpdate {
  title?: string;
  dueAt?: string;
  ownerId?: number;
}
