import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { tr } from '../../../core/i18n/translate';
import {
  PaidReportFilters,
  PaidReportFormat,
  PaidReportPage,
  PaidReportPageDto,
  toPaidReportPage,
} from '../models/paid-report';

/** Mensaje legible de un error de la API del reporte (`detail` o el primer error de un campo). */
export function paidReportErrorMessage(err: HttpErrorResponse): string {
  if (err.status === 0) return tr('CUSTOMERS.CUSTOMERS_API_SERVICE.NO_SE_PUDO_CONECTAR_CON');
  const body: unknown = err.error;
  if (body && typeof body === 'object') {
    for (const value of Object.values(body as Record<string, unknown>)) {
      const first = Array.isArray(value) ? value[0] : value;
      if (typeof first === 'string') return first;
    }
  }
  return tr('CUSTOMERS.CUSTOMERS_API_SERVICE.OCURRIO_UN_ERROR_INESPERADO_INTENTALO');
}

/** Reporte «Ingresos por venta»: lista paginada y exportación a PDF o Excel con los mismos filtros. */
@Injectable({ providedIn: 'root' })
export class PaidReportApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/orders/paid-report/`;

  list(filters: PaidReportFilters, page: number, pageSize: number): Observable<PaidReportPage> {
    const params = this.filterParams(filters).set('page', String(page)).set('page_size', String(pageSize));
    return this.http.get<PaidReportPageDto>(this.baseUrl, { params }).pipe(
      map(toPaidReportPage),
      catchError((err: HttpErrorResponse) => throwError(() => new Error(paidReportErrorMessage(err)))),
    );
  }

  export(format: PaidReportFormat, filters: PaidReportFilters): Observable<Blob> {
    return this.http
      .get(`${this.baseUrl}export/${format}/`, { params: this.filterParams(filters), responseType: 'blob' })
      .pipe(catchError((err: HttpErrorResponse) => throwError(() => new Error(this.exportMessage(err)))));
  }

  private exportMessage(err: HttpErrorResponse): string {
    // Con `responseType: 'blob'` el cuerpo del error llega como Blob; el límite de filas es el único 400 esperado.
    return err.status === 400 ? tr('SALES.PAID_REPORT.EXPORT_TOO_LARGE') : paidReportErrorMessage(err);
  }

  private filterParams(filters: PaidReportFilters): HttpParams {
    let params = new HttpParams();
    if (filters.dateFrom) params = params.set('date_from', filters.dateFrom);
    if (filters.dateTo) params = params.set('date_to', filters.dateTo);
    if (filters.fiscalPeriodId) params = params.set('fiscal_period_id', filters.fiscalPeriodId);
    return params;
  }
}
