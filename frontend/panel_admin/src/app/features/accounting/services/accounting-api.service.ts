import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import {
  Account,
  AccountClassCode,
  AccountClassState,
  AccountDto,
  AccountInput,
  AccountingSettings,
  AccountingSettingsDto,
  Classification,
  ClassificationDto,
  ClassificationInput,
  Direction,
  PaymentMethod,
  PaymentMethodDto,
  toApiError,
} from '../models/accounting';

export function toAccount(dto: AccountDto): Account {
  return {
    id: dto.id,
    name: dto.name,
    currency: dto.currency,
    kind: dto.kind ?? null,
    accountClass: dto.account_class ?? null,
    code: dto.code ?? null,
    isContra: dto.is_contra ?? false,
    hasEntries: dto.has_entries ?? false,
    openingBalance: dto.opening_balance ?? '0.00',
    isActive: dto.is_active,
  };
}

export function toSettings(dto: AccountingSettingsDto): AccountingSettings {
  return { cutoffDate: dto.cutoff_date, enabledAt: dto.enabled_at, locked: dto.locked, gaps: dto.gaps };
}

export function toClassification(dto: ClassificationDto): Classification {
  return { id: dto.id, name: dto.name, direction: dto.direction, isActive: dto.is_active };
}

export function toPaymentMethod(dto: PaymentMethodDto): PaymentMethod {
  return { code: dto.code, label: dto.label, isActive: dto.is_active, account: dto.account ? toAccount(dto.account) : null };
}

function toAccountBody(input: Partial<AccountInput>): Record<string, string | boolean | null | undefined> {
  const { openingBalance, accountClass, isContra, ...rest } = input;
  const body: Record<string, string | boolean | null | undefined> = { ...rest };
  if (openingBalance !== undefined) body['opening_balance'] = openingBalance;
  if (accountClass !== undefined) body['account_class'] = accountClass;
  if (isContra !== undefined) body['is_contra'] = isContra;
  return body;
}

/** Cuentas destino y mapeo método de pago → cuenta de la empresa (API `/api/accounting/`). */
@Injectable({ providedIn: 'root' })
export class AccountingApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/accounting/`;

  listAccounts(active?: boolean, accountClass?: AccountClassCode): Observable<Account[]> {
    let params = new HttpParams();
    if (active !== undefined) params = params.set('active', String(active));
    if (accountClass) params = params.set('account_class', accountClass);
    return this.request(this.http.get<AccountDto[]>(`${this.baseUrl}accounts/`, { params }), (rows) => rows.map(toAccount));
  }

  createAccount(input: AccountInput): Observable<Account> {
    return this.request(this.http.post<AccountDto>(`${this.baseUrl}accounts/`, toAccountBody(input)), toAccount);
  }

  updateAccount(id: string, input: Partial<AccountInput>): Observable<Account> {
    return this.request(this.http.patch<AccountDto>(`${this.baseUrl}accounts/${id}/`, toAccountBody(input)), toAccount);
  }

  activateAccount(id: string): Observable<Account> {
    return this.request(this.http.post<AccountDto>(`${this.baseUrl}accounts/${id}/activate/`, {}), toAccount);
  }

  deactivateAccount(id: string): Observable<Account> {
    return this.request(this.http.post<AccountDto>(`${this.baseUrl}accounts/${id}/deactivate/`, {}), toAccount);
  }

  getSettings(): Observable<AccountingSettings> {
    return this.request(this.http.get<AccountingSettingsDto>(`${this.baseUrl}settings/`), toSettings);
  }

  updateCutoff(cutoffDate: string): Observable<AccountingSettings> {
    return this.request(this.http.patch<AccountingSettingsDto>(`${this.baseUrl}settings/`, { cutoff_date: cutoffDate }), toSettings);
  }

  listAccountClasses(): Observable<AccountClassState[]> {
    return this.request(this.http.get<AccountClassState[]>(`${this.baseUrl}account-classes/`), (rows) => rows);
  }

  setAccountClassEnabled(code: AccountClassCode, enabled: boolean): Observable<AccountClassState> {
    const action = enabled ? 'enable' : 'disable';
    return this.request(this.http.post<AccountClassState>(`${this.baseUrl}account-classes/${code}/${action}/`, {}), (row) => row);
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
