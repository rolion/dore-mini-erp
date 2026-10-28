export const UNIT_NAME_MAX_LENGTH = 100;
export const UNIT_ABBREVIATION_MAX_LENGTH = 10;

/** Unidad de medida. `inUse` indica que algún producto la tiene como unidad base (no cambia su significado). */
export interface Unit {
  id: string;
  name: string;
  abbreviation: string;
  allowsFractions: boolean;
  active: boolean;
  inUse: boolean;
}

export interface UnitInput {
  name: string;
  abbreviation: string;
  allowsFractions: boolean;
}

export interface UnitDto {
  id: string;
  name: string;
  abbreviation: string;
  allows_fractions: boolean;
  active: boolean;
  in_use: boolean;
}

export interface ListParams {
  search?: string;
  active?: boolean;
  /** Página base 1. */
  page?: number;
  pageSize?: number;
}
