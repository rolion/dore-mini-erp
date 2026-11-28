import { CrmOwner } from './opportunity';

export type InboxScope = 'mine' | 'unassigned' | 'all';
export type InboxMessageStatus = 'queued' | 'sent' | 'delivered' | 'read' | 'failed';

export interface InboxContactRef {
  type: 'customer' | 'lead';
  id: string;
  name: string;
}

export interface InboxLastMessage {
  type: string;
  preview: string;
  direction: 'in' | 'out';
  status: InboxMessageStatus;
  at: string | null;
}

export interface InboxConversation {
  id: string;
  phone: string;
  contact: InboxContactRef | null;
  owner: CrmOwner | null;
  opportunity: { id: string; title: string } | null;
  lastMessage: InboxLastMessage | null;
  windowOpen: boolean;
  windowExpiresAt: string | null;
  /** Solo viene en el detalle de una conversación. */
  connectionActive: boolean | null;
}

export interface InboxConversationDto {
  id: string;
  phone: string;
  contact: InboxContactRef | null;
  owner: CrmOwner | null;
  opportunity: { id: string; title: string } | null;
  last_message: InboxLastMessage | null;
  window_open: boolean;
  window_expires_at: string | null;
  connection_active?: boolean;
}

export interface InboxMessage {
  id: string;
  direction: 'in' | 'out';
  type: string;
  /** Texto a mostrar: el cuerpo, el nombre de la plantilla o «[tipo]» para lo que no es texto. */
  text: string;
  status: InboxMessageStatus;
  failureReason: string;
  createdAt: string;
}

export interface InboxMessageDto {
  id: string;
  direction: 'in' | 'out';
  type: string;
  content: Record<string, unknown>;
  status: InboxMessageStatus;
  failure_reason: string;
  created_at: string;
  sent_at: string | null;
}

export interface InboxTemplate {
  id: string;
  name: string;
  language: string;
}

export interface InboxListParams {
  scope?: InboxScope;
  search?: string;
  opportunityId?: string;
  page?: number;
  pageSize?: number;
}

export interface InboxPage {
  count: number;
  results: InboxConversation[];
}

export interface InboxNewOpportunity {
  boardId: string;
  title: string;
  amount: string;
}
