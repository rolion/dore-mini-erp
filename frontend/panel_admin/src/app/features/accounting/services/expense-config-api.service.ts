import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
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
    return new ExpenseConfigError(tr('CUSTOMERS.CUSTOMERS_API_SERVICE.NO_SE_PUDO_CONECTAR_CON'), 0);
  }
  return new ExpenseConfigError(firstMessage(err.error) ?? tr('CUSTOMERS.CUSTOMERS_API_SERVICE.OCURRIO_UN_ERROR_INESPERADO_INTENTALO'), err.status);
}

/** Configuración de la clasificación de egreso de las categorías de Gastos y de los pagos a proveedores. */
@Injectable({ providedIn: 'root' })
export class ExpenseConfigApiService {
  private http = inject(HttpClient);
  private readonly categoriesUrl = `${environment.apiUrl}/expense-categories/`;
  private readonly paymentUrl = `${environment.apiUrl}/purchases/payment-classification/`;

  /** Categorías activas (hasta 100 por página, el máximo del servidor). */
  listCategories(): Observable<CategoryConfig[]> {
    return this.http.get<Page<CategoryConfigDto>>(this.categoriesUrl, { params: { active: 'true', page_size: '100' } }).pipe(
      map((page) => page.results.map((c) => ({ id: c.id, name: c.name, classification: c.classification }))),
      catchError((err: HttpErrorResponse) => throwError(() => toError(err))),
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
