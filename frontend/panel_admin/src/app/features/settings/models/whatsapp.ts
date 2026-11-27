import { tr } from '../../../core/i18n/translate';

export type WhatsappStatus = 'pending' | 'active' | 'error' | 'disabled';

/** Conexión de la empresa. Solo trae NOMBRES de variables de entorno: el token y el App Secret nunca viajan. */
export interface WhatsappConnection {
  configured: boolean;
  webhookUrl: string;
  wabaId: string;
  phoneNumberId: string;
  displayPhone: string;
  secretRef: string;
  appSecretRef: string;
  verifyToken: string;
  status: WhatsappStatus | 'none';
  statusReason: string;
}

export interface WhatsappConnectionDto {
  configured: boolean;
  webhook_url: string;
  waba_id?: string;
  phone_number_id?: string;
  display_phone?: string;
  secret_ref?: string;
  app_secret_ref?: string;
  verify_token?: string;
  status?: WhatsappStatus;
  status_reason?: string;
}

export interface WhatsappConnectionInput {
  wabaId: string;
  phoneNumberId: string;
  displayPhone: string;
  secretRef: string;
  appSecretRef: string;
}

export interface WhatsappTemplate {
  id: string;
  name: string;
  language: string;
  category: string;
  status: string;
  syncedAt: string | null;
}

export interface WhatsappTemplateDto {
  id: string;
  name: string;
  language: string;
  category: string;
  status: string;
  synced_at: string | null;
}

export interface WhatsappTestResult {
  id: string;
  status: string;
}

export type WhatsappFieldErrors = Record<string, string>;

/** Error de la API con mensaje legible, código estable (`window_closed`, `template_not_approved`…) y errores por campo. */
export class WhatsappApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string | null = null,
    readonly fieldErrors: WhatsappFieldErrors = {},
  ) {
    super(message);
  }
}

/** Clase del badge de plantilla (design-system §3): el color siempre va con texto. */
export function templateBadge(status: string): string {
  switch (status) {
    case 'APPROVED':
      return 'col-green';
    case 'REJECTED':
      return 'col-red';
    case 'PAUSED':
    case 'DISABLED':
      return 'col-orange';
    default:
      return 'col-blue';
  }
}

export function templateStatusLabel(status: string): string {
  const key = ['APPROVED', 'REJECTED', 'PAUSED', 'PENDING', 'DISABLED'].includes(status) ? status : 'OTHER';
  return tr(`SETTINGS.WHATSAPP.TEMPLATE_STATUS.${key}`);
}
