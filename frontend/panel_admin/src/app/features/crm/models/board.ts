import { tr } from '../../../core/i18n/translate';
import { CrmContact } from './lead';

export const CRM_NAME_MAX_LENGTH = 80;

export interface CrmStage {
  id: string;
  name: string;
  position: number;
  isActive: boolean;
  /** Tarjetas en la etapa (0 hasta que existan las oportunidades de PB-CRM-004). */
  cardCount: number;
}

export interface CrmBoard {
  id: string;
  name: string;
  isActive: boolean;
  /** Solo etapas activas, ordenadas por posición. */
  stages: CrmStage[];
}

export interface CrmStageDto {
  id: string;
  name: string;
  position: number;
  is_active: boolean;
  card_count: number;
}

export interface CrmBoardDto {
  id: string;
  name: string;
  is_active: boolean;
  stages: CrmStageDto[];
}

/**
 * Primer mensaje del servidor por campo, con el nombre del campo en camelCase (`target_stage_id` → `targetStageId`).
 * `name` y `targetStageId` (tableros) se declaran para leerlos con punto; el resto, por índice.
 */
export interface CrmFieldErrors {
  name?: string;
  targetStageId?: string;
  [field: string]: string | undefined;
}

/** Error de la API de CRM con mensaje listo para mostrar. */
export class CrmApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly fieldErrors: CrmFieldErrors = {},
    /**
     * Código estable de un 409: `stage_has_cards`, `board_has_cards`, `stage_order_stale`, `board_has_no_stages`,
     * `already_closed`, `multiple_customer_matches`, `customer_required`, `order_*`, `sales_disabled`…
     */
    readonly code: string | null = null,
    readonly cardCount = 0,
    /** Clientes coincidentes de un 409 `multiple_customer_matches`. */
    readonly candidates: CrmContact[] = [],
  ) {
    super(message);
    this.name = 'CrmApiError';
  }
}

export const networkErrorMessage = (): string => tr('CRM.ERRORS.SIN_CONEXION');
export const genericErrorMessage = (): string => tr('CRM.ERRORS.INESPERADO');
