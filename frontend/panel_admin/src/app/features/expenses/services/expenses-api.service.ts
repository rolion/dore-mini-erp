import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { Page } from '../../../shared/models/page';
import { toApiError } from '../models/api-error';
import { Expense, ExpenseDto, ExpenseInput, ExpenseListParams } from '../models/expense';

/** Página de gastos más la suma de los vigentes del filtro (en todas las páginas). */
export interface ExpensePage extends Page<Expense> {
  totalAmount: string;
}

interface ExpensePageDto extends Page<ExpenseDto> {
  total_amount: string;
}

export function toExpense(dto: ExpenseDto): Expense {
  return {
    id: dto.id,
    description: dto.description,
    amount: dto.amount,
    expenseDate: dto.expense_date,
    category: dto.category,
    paymentMethod: dto.payment_method,
    supplierName: dto.supplier_name,
    notes: dto.notes ?? '',
    status: dto.status,
    voidedAt: dto.voided_at,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function toBody(input: Partial<ExpenseInput>): Record<string, string> {
  const body: Record<string, string> = {};
  if (input.description !== undefined) body['description'] = input.description;
  if (input.amount !== undefined) body['amount'] = input.amount;
  if (input.categoryId !== undefined) body['category_id'] = input.categoryId;
  if (input.expenseDate !== undefined) body['expense_date'] = input.expenseDate;
  if (input.paymentMethod !== undefined) body['payment_method'] = input.paymentMethod;
  if (input.supplierName !== undefined) body['supplier_name'] = input.supplierName;
  if (input.notes !== undefined) body['notes'] = input.notes;
  return body;
}

@Injectable({
  providedIn: 'root',
})
export class ExpensesApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/expenses/`;

  list(params: ExpenseListParams = {}): Observable<ExpensePage> {
    let httpParams = new HttpParams();
    if (params.dateFrom) httpParams = httpParams.set('date_from', params.dateFrom);
    if (params.dateTo) httpParams = httpParams.set('date_to', params.dateTo);
    if (params.categoryId) httpParams = httpParams.set('category_id', params.categoryId);
    if (params.status) httpParams = httpParams.set('status', params.status);
    if (params.page !== undefined) httpParams = httpParams.set('page', String(params.page));
    if (params.pageSize !== undefined) httpParams = httpParams.set('page_size', String(params.pageSize));
    return this.http.get<ExpensePageDto>(this.baseUrl, { params: httpParams }).pipe(
      map(
        (page): ExpensePage => ({
          count: page.count,
          next: page.next,
          previous: page.previous,
          results: page.results.map(toExpense),
          totalAmount: page.total_amount,
        }),
      ),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err.status, err.error))),
    );
  }

  get(id: string): Observable<Expense> {
    return this.request(this.http.get<ExpenseDto>(`${this.baseUrl}${id}/`));
  }

  create(input: ExpenseInput): Observable<Expense> {
    return this.request(this.http.post<ExpenseDto>(this.baseUrl, toBody(input)));
  }

  update(id: string, input: Partial<ExpenseInput>): Observable<Expense> {
    return this.request(this.http.patch<ExpenseDto>(`${this.baseUrl}${id}/`, toBody(input)));
  }

  /** Anula el gasto (irreversible): deja de sumar en los reportes. */
  void(id: string): Observable<Expense> {
    return this.request(this.http.post<ExpenseDto>(`${this.baseUrl}${id}/void/`, {}));
  }

  private request(source: Observable<ExpenseDto>): Observable<Expense> {
    return source.pipe(
      map(toExpense),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err.status, err.error))),
    );
  }
}
