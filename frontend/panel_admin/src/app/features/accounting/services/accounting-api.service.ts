import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import {
  Account,
  AccountDto,
  AccountInput,
  Classification,
  ClassificationDto,
  ClassificationInput,
  Direction,
  PaymentMethod,
  PaymentMethodDto,
  toApiError,
} from '../models/accounting';

export function toAccount(dto: AccountDto): Account {
  return { id: dto.id, name: dto.name, currency: dto.currency, kind: dto.kind ?? null, isActive: dto.is_active };
}

export function toClassification(dto: ClassificationDto): Classification {
  return { id: dto.id, name: dto.name, direction: dto.direction, isActive: dto.is_active };
}

export function toPaymentMethod(dto: PaymentMethodDto): PaymentMethod {
  return { code: dto.code, label: dto.label, isActive: dto.is_active, account: dto.account ? toAccount(dto.account) : null };
}

/** Cuentas destino y mapeo método de pago → cuenta de la empresa (API `/api/accounting/`). */
@Injectable({ providedIn: 'root' })
export class AccountingApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/accounting/`;

  listAccounts(active?: boolean): Observable<Account[]> {
    let params = new HttpParams();
    if (active !== undefined) params = params.set('active', String(active));
    return this.request(this.http.get<AccountDto[]>(`${this.baseUrl}accounts/`, { params }), (rows) => rows.map(toAccount));
  }

  createAccount(input: AccountInput): Observable<Account> {
    return this.request(this.http.post<AccountDto>(`${this.baseUrl}accounts/`, input), toAccount);
  }

  updateAccount(id: string, input: Partial<AccountInput>): Observable<Account> {
    return this.request(this.http.patch<AccountDto>(`${this.baseUrl}accounts/${id}/`, input), toAccount);
  }

  activateAccount(id: string): Observable<Account> {
    return this.request(this.http.post<AccountDto>(`${this.baseUrl}accounts/${id}/activate/`, {}), toAccount);
  }

  deactivateAccount(id: string): Observable<Account> {
    return this.request(this.http.post<AccountDto>(`${this.baseUrl}accounts/${id}/deactivate/`, {}), toAccount);
  }

  listClassifications(filters: { active?: boolean; direction?: Direction } = {}): Observable<Classification[]> {
    let params = new HttpParams();
    if (filters.active !== undefined) params = params.set('active', String(filters.active));
    if (filters.direction) params = params.set('direction', filters.direction);
    return this.request(this.http.get<ClassificationDto[]>(`${this.baseUrl}classifications/`, { params }), (rows) => rows.map(toClassification));
  }

  createClassification(input: ClassificationInput): Observable<Classification> {
    return this.request(this.http.post<ClassificationDto>(`${this.baseUrl}classifications/`, input), toClassification);
  }

  renameClassification(id: string, name: string): Observable<Classification> {
    return this.request(this.http.patch<ClassificationDto>(`${this.baseUrl}classifications/${id}/`, { name }), toClassification);
  }

  activateClassification(id: string): Observable<Classification> {
    return this.request(this.http.post<ClassificationDto>(`${this.baseUrl}classifications/${id}/activate/`, {}), toClassification);
  }

  deactivateClassification(id: string): Observable<Classification> {
    return this.request(this.http.post<ClassificationDto>(`${this.baseUrl}classifications/${id}/deactivate/`, {}), toClassification);
  }

  listMethods(): Observable<PaymentMethod[]> {
    return this.request(this.http.get<PaymentMethodDto[]>(`${this.baseUrl}payment-methods/`), (rows) => rows.map(toPaymentMethod));
  }

  configureMethod(code: string, accountId: string | null, isActive: boolean): Observable<PaymentMethod> {
    return this.request(
      this.http.put<PaymentMethodDto>(`${this.baseUrl}payment-methods/${code}/`, { account_id: accountId, is_active: isActive }),
      toPaymentMethod,
    );
  }

  private request<D, T>(source: Observable<D>, convert: (dto: D) => T): Observable<T> {
    return source.pipe(
      map(convert),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err.status, err.error))),
    );
  }
}
