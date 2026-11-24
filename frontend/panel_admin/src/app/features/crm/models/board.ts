import { tr } from '../../../core/i18n/translate';

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

/** Error de la API de CRM con mensaje listo para mostrar. */
export class CrmApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly fieldErrors: Partial<Record<'name' | 'targetStageId', string>> = {},
    /** Código estable de un 409: `stage_has_cards`, `board_has_cards`, `stage_order_stale`. */
    readonly code: string | null = null,
    readonly cardCount = 0,
  ) {
    super(message);
    this.name = 'CrmApiError';
  }
}

export const networkErrorMessage = (): string => tr('CRM.ERRORS.SIN_CONEXION');
export const genericErrorMessage = (): string => tr('CRM.ERRORS.INESPERADO');
