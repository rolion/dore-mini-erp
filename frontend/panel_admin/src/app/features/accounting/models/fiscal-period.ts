export type FiscalPeriodStatus = 'OPEN' | 'CLOSED';

export interface FiscalPeriod {
  id: string;
  name: string;
  /** Fechas inclusivas `yyyy-MM-dd`. */
  startDate: string;
  endDate: string;
  status: FiscalPeriodStatus;
  isOpen: boolean;
  closedByName: string;
}

export interface FiscalPeriodInput {
  name: string;
  startDate: string;
  endDate: string;
}

export interface FiscalPeriodDto {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  status: FiscalPeriodStatus;
  closed_by_name: string;
}

export function toFiscalPeriod(dto: FiscalPeriodDto): FiscalPeriod {
  return {
    id: dto.id,
    name: dto.name,
    startDate: dto.start_date,
    endDate: dto.end_date,
    status: dto.status,
    isOpen: dto.status === 'OPEN',
    closedByName: dto.closed_by_name,
  };
}
