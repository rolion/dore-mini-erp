import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { EMPTY, Observable, catchError, expand, map, reduce, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { tr } from '../../../core/i18n/translate';
import { Page } from '../../../shared/models/page';
import {
  CategoryConfig,
  CategoryConfigDto,
  ClassificationRef,
  ExpenseConfigError,
  PaymentClassificationDto,
} from '../models/expense-config';

/** Primer mensaje legible del cuerpo de error de DRF (`{campo: [mensajes]}` o `{detail}`). */
export function firstMessage(body: unknown): string | null {
  if (body && typeof body === 'object') {
    for (const value of Object.values(body as Record<string, unknown>)) {
      if (Array.isArray(value) && typeof value[0] === 'string') {
        return value[0];
      }
      if (typeof value === 'string') {
        return value;
      }
    }
  }
  return null;
}

function toError(err: HttpErrorResponse): ExpenseConfigError {
  if (err.status === 0) {
    return new ExpenseConfigError(tr('ACCOUNTING.EXPENSE_CONFIG.ERROR_DE_RED'), 0);
  }
  return new ExpenseConfigError(firstMessage(err.error) ?? tr('ACCOUNTING.EXPENSE_CONFIG.ERROR_INESPERADO'), err.status);
}

/** Configuración de la clasificación de egreso de las categorías de Gastos y de los pagos a proveedores. */
@Injectable({ providedIn: 'root' })
export class ExpenseConfigApiService {
  private http = inject(HttpClient);
  private readonly categoriesUrl = `${environment.apiUrl}/expense-categories/`;
  private readonly paymentUrl = `${environment.apiUrl}/purchases/payment-classification/`;

  /** Todas las categorías activas: recorre las páginas del servidor (máximo 100 por página). */
  listCategories(): Observable<CategoryConfig[]> {
    return this.categoriesPage(1).pipe(
      expand((result) => (result.hasNext ? this.categoriesPage(result.page + 1) : EMPTY)),
      reduce((all, result) => [...all, ...result.rows], [] as CategoryConfig[]),
      catchError((err: HttpErrorResponse) => throwError(() => toError(err))),
    );
  }

  private categoriesPage(page: number): Observable<{ page: number; hasNext: boolean; rows: CategoryConfig[] }> {
    const params = { active: 'true', page_size: '100', page: String(page) };
    return this.http.get<Page<CategoryConfigDto>>(this.categoriesUrl, { params }).pipe(
      map((body) => ({
        page,
        hasNext: !!body.next,
        rows: body.results.map((c) => ({ id: c.id, name: c.name, classification: c.classification })),
      })),
    );
  }

  setCategoryClassification(categoryId: string, classificationId: string | null): Observable<ClassificationRef | null> {
    return this.http.put<CategoryConfigDto>(`${this.categoriesUrl}${categoryId}/classification/`, { classification_id: classificationId }).pipe(
      map((c) => c.classification),
      catchError((err: HttpErrorResponse) => throwError(() => toError(err))),
    );
  }

  getPaymentClassification(): Observable<ClassificationRef | null> {
    return this.http.get<PaymentClassificationDto>(this.paymentUrl).pipe(
      map((body) => body.classification),
      catchError((err: HttpErrorResponse) => throwError(() => toError(err))),
    );
  }

  setPaymentClassification(classificationId: string | null): Observable<ClassificationRef | null> {
    return this.http.put<PaymentClassificationDto>(this.paymentUrl, { classification_id: classificationId }).pipe(
      map((body) => body.classification),
      catchError((err: HttpErrorResponse) => throwError(() => toError(err))),
    );
  }
}
