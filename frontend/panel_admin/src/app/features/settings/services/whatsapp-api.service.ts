import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, OperatorFunction, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { tr } from '../../../core/i18n/translate';
import {
  WhatsappApiError, WhatsappConnection, WhatsappConnectionDto, WhatsappConnectionInput, WhatsappFieldErrors,
  WhatsappTemplate, WhatsappTemplateDto, WhatsappTestResult,
} from '../models/whatsapp';

const camel = (key: string): string => key.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase());

function text(value: unknown): string | undefined {
  if (typeof value === 'string') return value;
  return Array.isArray(value) && value.length ? value.map(String).join(' ') : undefined;
}

export function toWhatsappError(error: HttpErrorResponse): WhatsappApiError {
  if (error.status === 0) return new WhatsappApiError(tr('SETTINGS.WHATSAPP.ERROR_RED'), 0);
  const body = (error.error && typeof error.error === 'object' ? error.error : {}) as Record<string, unknown>;
  const code = typeof body['code'] === 'string' ? body['code'] : null;
  const fields: WhatsappFieldErrors = {};
  if (error.status === 400) {
    for (const [key, value] of Object.entries(body)) {
      const message = text(value);
      if (message && key !== 'detail' && key !== 'code') fields[camel(key)] = message;
    }
  }
  const known = code ? tr(`SETTINGS.WHATSAPP.ERRORS.${code.toUpperCase()}`) : '';
  const message = known && !known.startsWith('SETTINGS.') ? known : (text(body['detail']) ?? tr('SETTINGS.WHATSAPP.ERROR_GENERICO'));
  return new WhatsappApiError(message, error.status, code, fields);
}

function whatsappErrors<T>(): OperatorFunction<T, T> {
  return (source) => source.pipe(catchError((err: HttpErrorResponse) => throwError(() => toWhatsappError(err))));
}

export function toConnection(dto: WhatsappConnectionDto): WhatsappConnection {
  return {
    configured: dto.configured,
    webhookUrl: dto.webhook_url,
    secretRefPrefix: dto.secret_ref_prefix ?? '',
    wabaId: dto.waba_id ?? '',
    phoneNumberId: dto.phone_number_id ?? '',
    displayPhone: dto.display_phone ?? '',
    secretRef: dto.secret_ref ?? '',
    appSecretRef: dto.app_secret_ref ?? '',
    verifyToken: dto.verify_token ?? '',
    status: dto.configured ? (dto.status ?? 'pending') : 'none',
    statusReason: dto.status_reason ?? '',
  };
}

export function toTemplate(dto: WhatsappTemplateDto): WhatsappTemplate {
  return {
    id: dto.id, name: dto.name, language: dto.language, category: dto.category, status: dto.status,
    syncedAt: dto.synced_at,
  };
}

/** Integración de WhatsApp (`/api/messaging/whatsapp/`). Los errores llegan como `WhatsappApiError`. */
@Injectable({ providedIn: 'root' })
export class WhatsappApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/messaging/whatsapp/`;

  getConnection(): Observable<WhatsappConnection> {
    return this.http.get<WhatsappConnectionDto>(`${this.baseUrl}connection/`).pipe(map(toConnection), whatsappErrors());
  }

  saveConnection(input: WhatsappConnectionInput): Observable<WhatsappConnection> {
    const body = {
      waba_id: input.wabaId.trim(),
      phone_number_id: input.phoneNumberId.trim(),
      display_phone: input.displayPhone.trim(),
      secret_ref: input.secretRef.trim(),
      app_secret_ref: input.appSecretRef.trim(),
    };
    return this.http.put<WhatsappConnectionDto>(`${this.baseUrl}connection/`, body).pipe(map(toConnection), whatsappErrors());
  }

  listTemplates(): Observable<WhatsappTemplate[]> {
    return this.http.get<{ results: WhatsappTemplateDto[] }>(`${this.baseUrl}templates/`).pipe(
      map((page) => page.results.map(toTemplate)), whatsappErrors());
  }

  syncTemplates(): Observable<WhatsappTemplate[]> {
    return this.http.post<{ results: WhatsappTemplateDto[] }>(`${this.baseUrl}templates/sync/`, {}).pipe(
      map((page) => page.results.map(toTemplate)), whatsappErrors());
  }

  sendTestMessage(to: string, templateId: string): Observable<WhatsappTestResult> {
    return this.http.post<WhatsappTestResult>(`${this.baseUrl}test-message/`, { to: to.trim(), template_id: templateId }).pipe(
      whatsappErrors());
  }
}
