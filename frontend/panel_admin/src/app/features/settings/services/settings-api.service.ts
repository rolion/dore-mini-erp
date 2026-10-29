import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import {
  HistoryFilters,
  ModuleSettings,
  SETTINGS_ERROR_MESSAGE,
  SettingHistoryPage,
  SettingsApiError,
} from '../models/setting';

interface SettingDto {
  key: string;
  label: string;
  description: string;
  kind: 'choice' | 'percent' | 'boolean';
  value: string;
  default: string;
  choices: { value: string; label: string }[];
  minimum: string | null;
  maximum: string | null;
}

interface ModuleSettingsDto {
  module: string;
  settings: SettingDto[];
}

interface HistoryDto {
  count: number;
  results: {
    id: string;
    changed_at: string;
    changed_by: string;
    setting_key: string;
    setting_label: string;
    old_value: string;
    new_value: string;
  }[];
  settings: { key: string; label: string }[];
}

interface ErrorBody {
  detail?: unknown;
  settings?: unknown;
  date_from?: unknown;
  date_to?: unknown;
}

/** Ajustes por módulo de la empresa del usuario y su historial de cambios. */
@Injectable({
  providedIn: 'root',
})
export class SettingsApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/settings/`;

  get(module: string): Observable<ModuleSettings> {
    return this.http.get<ModuleSettingsDto>(`${this.baseUrl}${module}/`).pipe(
      map((dto) => dto as ModuleSettings),
      catchError((err: HttpErrorResponse) => throwError(() => this.toError(err))),
    );
  }

  /** Guarda en bloque los valores indicados (`clave -> valor`); la API es todo o nada. */
  save(module: string, values: Record<string, string>): Observable<ModuleSettings> {
    return this.http.patch<ModuleSettingsDto>(`${this.baseUrl}${module}/`, { settings: values }).pipe(
      map((dto) => dto as ModuleSettings),
      catchError((err: HttpErrorResponse) => throwError(() => this.toError(err))),
    );
  }

  history(scope: string, filters: HistoryFilters): Observable<SettingHistoryPage> {
    let params = new HttpParams().set('page', String(filters.page));
    if (filters.dateFrom) {
      params = params.set('date_from', filters.dateFrom);
    }
    if (filters.dateTo) {
      params = params.set('date_to', filters.dateTo);
    }
    if (filters.setting) {
      params = params.set('setting', filters.setting);
    }
    return this.http.get<HistoryDto>(`${this.baseUrl}${scope}/history/`, { params }).pipe(
      map((dto) => ({
        count: dto.count,
        settings: dto.settings,
        results: dto.results.map((row) => ({
          id: row.id,
          changedAt: row.changed_at,
          changedBy: row.changed_by,
          settingKey: row.setting_key,
          settingLabel: row.setting_label,
          oldValue: row.old_value,
          newValue: row.new_value,
        })),
      })),
      catchError((err: HttpErrorResponse) => throwError(() => this.toError(err))),
    );
  }

  private toError(err: HttpErrorResponse): SettingsApiError {
    const body = (err.error && typeof err.error === 'object' ? err.error : {}) as ErrorBody;
    const fieldErrors: Record<string, string> = {};
    if (body.settings && typeof body.settings === 'object' && !Array.isArray(body.settings)) {
      for (const [key, messages] of Object.entries(body.settings as Record<string, unknown>)) {
        fieldErrors[key] = Array.isArray(messages) ? messages.map(String).join(' ') : String(messages);
      }
    }
    const detail =
      typeof body.detail === 'string'
        ? body.detail
        : [body.date_from, body.date_to].flat().find((m): m is string => typeof m === 'string');
    const message = err.status === 0 ? SETTINGS_ERROR_MESSAGE : detail || SETTINGS_ERROR_MESSAGE;
    return new SettingsApiError(message, err.status, fieldErrors);
  }
}
