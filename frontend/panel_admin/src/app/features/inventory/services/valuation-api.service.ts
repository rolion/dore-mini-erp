import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import {
  Adoption,
  AdoptionInput,
  Proposal,
  ProposalBlocker,
  ProposalDto,
  Valuation,
  ValuationDto,
} from '../models/valuation';

const GENERIC_MESSAGE = 'Ocurrió un error inesperado. Inténtalo de nuevo.';
const NETWORK_MESSAGE = 'No se pudo conectar con el servidor. Inténtalo de nuevo.';
const VALIDATION_MESSAGE = 'Revisa los valores ingresados.';

/** Errores por campo de una línea de la adopción (misma posición que las líneas enviadas). */
export type ValuationLineErrors = Partial<Record<'totalValue' | 'reconciledQuantity' | 'productId' | 'source', string[]>>;

export class ValuationApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    /** Código estable de un 409: `negative_stock`, `stock_changed`, `valuation_already_adopted`, ... */
    readonly code: string | null = null,
    readonly lineErrors: ValuationLineErrors[] = [],
    readonly blockers: ProposalBlocker[] = [],
  ) {
    super(message);
    this.name = 'ValuationApiError';
  }
}

function toLineErrors(line: unknown): ValuationLineErrors {
  const record = (line && typeof line === 'object' ? line : {}) as Record<string, unknown>;
  const pick = (key: string): string[] | undefined => (Array.isArray(record[key]) ? (record[key] as unknown[]).map(String) : undefined);
  return {
    totalValue: pick('total_value'),
    reconciledQuantity: pick('reconciled_quantity'),
    productId: pick('product_id'),
    source: pick('source'),
  };
}

export function toValuationError(status: number, body: unknown): ValuationApiError {
  if (status === 0) {
    return new ValuationApiError(NETWORK_MESSAGE, 0);
  }
  const record = (body && typeof body === 'object' ? body : {}) as Record<string, unknown>;
  if (status === 400) {
    const lines = Array.isArray(record['lines']) ? (record['lines'] as unknown[]).map(toLineErrors) : [];
    return new ValuationApiError(VALIDATION_MESSAGE, 400, null, lines);
  }
  const detail = typeof record['detail'] === 'string' ? record['detail'] : '';
  const code = typeof record['code'] === 'string' ? record['code'] : null;
  if (status === 409) {
    const blockers = Array.isArray(record['blockers'])
      ? (record['blockers'] as ProposalBlockerLike[]).map(toBlocker)
      : [];
    return new ValuationApiError(detail || GENERIC_MESSAGE, 409, code, [], blockers);
  }
  return new ValuationApiError(detail || GENERIC_MESSAGE, status, code);
}

type ProposalBlockerLike = ProposalDto['blockers'][number];

function toBlocker(dto: ProposalBlockerLike): ProposalBlocker {
  return {
    productId: dto.product_id,
    productName: dto.product_name,
    warehouseId: dto.warehouse_id,
    warehouseName: dto.warehouse_name,
    quantity: dto.quantity,
  };
}

function toValuation(dto: ValuationDto): Valuation {
  const adoption = dto.adoption;
  return {
    status: dto.status,
    adoption: adoption
      ? {
          id: adoption.id,
          cutoffAt: adoption.cutoff_at,
          method: adoption.method,
          userName: adoption.user_name,
          lines: adoption.lines.map((line) => ({
            productId: line.product_id,
            productName: line.product_name,
            unitAbbreviation: line.unit_abbreviation,
            reconciledQuantity: line.reconciled_quantity,
            totalValue: line.total_value,
            unitCost: line.unit_cost,
            declaredZero: line.declared_zero,
            source: line.source,
          })),
        }
      : null,
  };
}

function toProposal(dto: ProposalDto): Proposal {
  return {
    lines: dto.lines.map((line) => ({
      productId: line.product_id,
      productName: line.product_name,
      unitAbbreviation: line.unit_abbreviation,
      reconciledQuantity: line.reconciled_quantity,
      warehouses: line.warehouses.map((w) => ({
        warehouseId: w.warehouse_id,
        warehouseName: w.warehouse_name,
        quantity: w.quantity,
      })),
    })),
    blockers: dto.blockers.map(toBlocker),
  };
}

/** Valoración inicial del inventario (`/api/valuation/`, módulo Costeo). */
@Injectable({
  providedIn: 'root',
})
export class ValuationApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/valuation/`;

  get(): Observable<Valuation> {
    return this.http.get<ValuationDto>(this.baseUrl).pipe(
      map(toValuation),
      catchError((err: HttpErrorResponse) => throwError(() => toValuationError(err.status, err.error))),
    );
  }

  proposal(): Observable<Proposal> {
    return this.http.get<ProposalDto>(`${this.baseUrl}proposal/`).pipe(
      map(toProposal),
      catchError((err: HttpErrorResponse) => throwError(() => toValuationError(err.status, err.error))),
    );
  }

  /** Confirma la adopción; reenviar el mismo `adoptionId` devuelve la original sin duplicarla. */
  adopt(input: AdoptionInput): Observable<Adoption> {
    const body = {
      adoption_id: input.adoptionId,
      lines: input.lines.map((line) => ({
        product_id: line.productId,
        reconciled_quantity: line.reconciledQuantity,
        total_value: line.totalValue.trim() === '' ? null : line.totalValue.trim(),
        declared_zero: line.declaredZero,
        source: line.source.trim() === '' ? null : line.source.trim(),
      })),
    };
    return this.http.post<ValuationDto>(`${this.baseUrl}adopt/`, body).pipe(
      map((dto) => toValuation(dto).adoption as Adoption),
      catchError((err: HttpErrorResponse) => throwError(() => toValuationError(err.status, err.error))),
    );
  }
}
