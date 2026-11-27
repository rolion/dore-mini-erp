import { CrmContact } from './lead';

export const CRM_OPPORTUNITY_TITLE_MAX_LENGTH = 150;
export const CRM_LOST_REASON_MAX_LENGTH = 500;
export const CRM_OPPORTUNITY_DESCRIPTION_MAX_LENGTH = 1000;
/** Importe con hasta 2 decimales, sin signo (el servidor exige `amount` ≥ 0 en `Decimal(12,2)`). */
export const CRM_AMOUNT_PATTERN = /^\d{1,10}(\.\d{1,2})?$/;
/** Tarjetas que el tablero pide de una vez (el servidor limita la página a 200). */
export const CRM_BOARD_PAGE_SIZE = 200;

export type CrmOpportunityStatus = 'open' | 'won' | 'lost';
export type CrmCloseResult = 'won' | 'lost';

/** Responsable: usuario de la empresa. El id es entero, como el usuario de Django. */
export interface CrmOwner {
  id: number;
  name: string;
}

export interface CrmOpportunityDto {
  id: string;
  board_id: string;
  stage_id: string;
  lead: CrmContact | null;
  customer: CrmContact | null;
  title: string;
  description: string;
  owner: CrmOwner;
  amount: string;
  currency: string;
  next_action_at: string | null;
  status: CrmOpportunityStatus;
  closed_at: string | null;
  order_id: string | null;
  lost_reason: string;
  created_at: string;
}

export interface CrmOpportunityPageDto {
  count: number;
  next: string | null;
  previous: string | null;
  results: CrmOpportunityDto[];
}

export interface CrmOpportunity {
  id: string;
  boardId: string;
  stageId: string;
  lead: CrmContact | null;
  customer: CrmContact | null;
  title: string;
  description: string;
  owner: CrmOwner;
  /** Decimal como texto, tal como lo entrega el servidor. */
  amount: string;
  currency: string;
  nextActionAt: string | null;
  status: CrmOpportunityStatus;
  closedAt: string | null;
  orderId: string | null;
  lostReason: string;
  createdAt: string;
}

export interface CrmOpportunityPage {
  count: number;
  results: CrmOpportunity[];
}

export interface CrmOpportunityFilters {
  boardId: string;
  ownerId?: number;
  leadId?: string;
  customerId?: string;
  status?: CrmOpportunityStatus;
  page?: number;
  pageSize?: number;
}

export interface CrmOpportunityCreate {
  boardId: string;
  stageId?: string;
  leadId?: string;
  customerId?: string;
  title: string;
  /** Opcional: sin importe el servidor guarda 0.00 (tarjetas de seguimiento). */
  amount?: string;
  description?: string;
  nextActionAt?: string | null;
  ownerId?: number;
}

export interface CrmOpportunityUpdate {
  title?: string;
  amount?: string;
  description?: string;
  nextActionAt?: string | null;
  ownerId?: number;
}

export interface CrmCloseInput {
  result: CrmCloseResult;
  lostReason?: string;
  orderId?: string;
}

export interface CrmLinkableOrderDto {
  id: string;
  order_date: string;
  total: string;
  status: string;
}

export interface CrmLinkableOrder {
  id: string;
  orderDate: string;
  total: string;
  status: string;
}

export interface CrmStageChangeDto {
  from_stage_id: string | null;
  to_stage_id: string;
  changed_by: number | null;
  changed_at: string;
}

export interface CrmStageChange {
  fromStageId: string | null;
  toStageId: string;
  changedBy: number | null;
  changedAt: string;
}

/** Contacto que muestra la tarjeta: el cliente si ya lo hay; si no, el prospecto. */
export function opportunityContact(opportunity: CrmOpportunity): CrmContact | null {
  return opportunity.customer ?? opportunity.lead;
}

/** La siguiente acción venció si su fecha ya pasó (solo para oportunidades abiertas). */
export function isOverdue(opportunity: CrmOpportunity, now: Date = new Date()): boolean {
  return opportunity.status === 'open' && !!opportunity.nextActionAt
    && new Date(opportunity.nextActionAt).getTime() < now.getTime();
}
