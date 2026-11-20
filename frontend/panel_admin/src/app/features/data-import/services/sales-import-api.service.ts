import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { tr } from '../../../core/i18n/translate';
import { Page } from '../../../shared/models/page';
import { PostingIssue } from '../../../shared/models/receivable';
import {
  ImportApiError,
  ImportCapabilities,
  ImportCounts,
  ImportFieldErrors,
  ImportMapping,
  ImportPreview,
  ImportProblem,
  ImportRequest,
  ImportResult,
  ImportRow,
  ImportRowStatus,
  ImportRunDetail,
  ImportRunSummary,
  ImportUpload,
} from '../models/sales-import';

export const NETWORK_ERROR_MESSAGE = (): string => tr('DATA_IMPORT.ERR_NETWORK');
export const GENERIC_ERROR_MESSAGE = (): string => tr('DATA_IMPORT.ERR_GENERIC');
export const VALIDATION_ERROR_MESSAGE = (): string => tr('DATA_IMPORT.ERR_VALIDATION');
export const NOT_FOUND_MESSAGE = (): string => tr('DATA_IMPORT.ERR_NOT_FOUND');

interface CountsDto {
  created: number;
  skipped: number;
  failed: number;
  without_posting: number;
}

interface UploadDto {
  id: string;
  filename: string;
  row_count: number;
  headers: string[];
  sample_rows: string[][];
  suggested_mapping: ImportMapping;
  capabilities: {
    customers: boolean;
    inventory: boolean;
    purchases: boolean;
    accounting: boolean;
    costing: boolean;
    warehouses: { id: string; name: string; is_default: boolean }[];
    payment_methods: string[];
    sales_channels: string[];
  };
}

interface PreviewDto {
  sales_total: number;
  lines_total: number;
  to_create: number;
  already_imported: number;
  with_errors: number;
  new_products: number;
  existing_products: number;
  new_customers: number;
  existing_customers: number;
  purchases_to_create: number;
  units_to_buy: number;
  without_posting: number;
  problems: { row: number; sale_key: string; field: string; code: string; message: string }[];
  problems_total: number;
}

interface RunDto {
  id: string;
  filename: string;
  status: string;
  created_at: string;
  created_by_name: string;
  row_count: number;
  counts: CountsDto;
  options?: Record<string, unknown>;
}

interface RowDto {
  row: number;
  sale_key: string;
  status: ImportRowStatus;
  code: string;
  message: string;
  order_id: string | null;
}

function toCounts(dto: CountsDto): ImportCounts {
  return { created: dto.created, skipped: dto.skipped, failed: dto.failed, withoutPosting: dto.without_posting };
}

function toCapabilities(dto: UploadDto['capabilities']): ImportCapabilities {
  return {
    customers: dto.customers,
    inventory: dto.inventory,
    purchases: dto.purchases,
    accounting: dto.accounting,
    costing: dto.costing,
    warehouses: dto.warehouses.map((w) => ({ id: w.id, name: w.name, isDefault: w.is_default })),
    paymentMethods: dto.payment_methods,
    salesChannels: dto.sales_channels,
  };
}

function toUpload(dto: UploadDto): ImportUpload {
  return {
    id: dto.id,
    filename: dto.filename,
    rowCount: dto.row_count,
    headers: dto.headers,
    sampleRows: dto.sample_rows,
    suggestedMapping: dto.suggested_mapping,
    capabilities: toCapabilities(dto.capabilities),
  };
}

function toProblem(dto: PreviewDto['problems'][number]): ImportProblem {
  return { row: dto.row, saleKey: dto.sale_key, field: dto.field, code: dto.code, message: dto.message };
}

function toPreview(dto: PreviewDto): ImportPreview {
  return {
    salesTotal: dto.sales_total,
    linesTotal: dto.lines_total,
    toCreate: dto.to_create,
    alreadyImported: dto.already_imported,
    withErrors: dto.with_errors,
    newProducts: dto.new_products,
    existingProducts: dto.existing_products,
    newCustomers: dto.new_customers,
    existingCustomers: dto.existing_customers,
    purchasesToCreate: dto.purchases_to_create,
    unitsToBuy: dto.units_to_buy,
    withoutPosting: dto.without_posting,
    problems: dto.problems.map(toProblem),
    problemsTotal: dto.problems_total,
  };
}

function toRun(dto: RunDto): ImportRunSummary {
  return {
    id: dto.id,
    filename: dto.filename,
    status: dto.status,
    createdAt: dto.created_at,
    createdByName: dto.created_by_name,
    rowCount: dto.row_count,
    counts: toCounts(dto.counts),
  };
}

function toRow(dto: RowDto): ImportRow {
  return {
    row: dto.row,
    saleKey: dto.sale_key,
    status: dto.status,
    code: dto.code,
    message: dto.message,
    orderId: dto.order_id,
  };
}

function toFieldErrors(body: unknown): ImportFieldErrors {
  const errors: ImportFieldErrors = {};
  if (body && typeof body === 'object') {
    for (const [name, value] of Object.entries(body as Record<string, unknown>)) {
      if (Array.isArray(value)) {
        errors[name] = value.map(String);
      } else if (typeof value === 'string' && name === 'detail') {
        errors[name] = [value];
      }
    }
  }
  return errors;
}

function toPostingIssues(body: unknown): PostingIssue[] {
  const raw = (body as { issues?: unknown } | null)?.issues;
  if (!Array.isArray(raw)) return [];
  return raw
    .filter((item): item is { code: string; subject: string; message: string } =>
      !!item && typeof item === 'object' && typeof (item as { message?: unknown }).message === 'string')
    .map((item) => ({ code: String(item.code ?? ''), subject: String(item.subject ?? ''), message: item.message }));
}

function toApiError(err: HttpErrorResponse): ImportApiError {
  if (err.status === 0) {
    return new ImportApiError(NETWORK_ERROR_MESSAGE(), 0);
  }
  const body = err.error as { detail?: unknown; code?: unknown } | null;
  const detail = typeof body?.detail === 'string' ? body.detail : '';
  if (err.status === 400) {
    return new ImportApiError(detail || VALIDATION_ERROR_MESSAGE(), 400, '', toFieldErrors(err.error));
  }
  if (err.status === 404) {
    return new ImportApiError(detail || NOT_FOUND_MESSAGE(), 404);
  }
  if (err.status === 409 && typeof body?.code === 'string') {
    return new ImportApiError(
      detail || GENERIC_ERROR_MESSAGE(),
      409,
      body.code,
      {},
      body.code === 'posting_configuration_missing' ? toPostingIssues(err.error) : [],
    );
  }
  return new ImportApiError(GENERIC_ERROR_MESSAGE(), err.status);
}

function toBody(request: ImportRequest): Record<string, unknown> {
  const o = request.options;
  return {
    mapping: request.mapping,
    options: {
      infer_products: o.inferProducts,
      infer_customers: o.inferCustomers,
      infer_inventory: o.inferInventory,
      infer_accounting: o.inferAccounting,
      default_payment_method: o.defaultPaymentMethod,
      default_sales_channel: o.defaultSalesChannel,
      warehouse_id: o.warehouseId,
      date_format: o.dateFormat,
    },
  };
}

@Injectable({ providedIn: 'root' })
export class SalesImportApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/imports/sales/`;

  upload(file: File): Observable<ImportUpload> {
    const form = new FormData();
    form.append('file', file);
    return this.http.post<UploadDto>(this.baseUrl, form).pipe(map(toUpload), this.fail());
  }

  preview(id: string, request: ImportRequest): Observable<ImportPreview> {
    return this.http.post<PreviewDto>(`${this.baseUrl}${id}/preview/`, toBody(request)).pipe(map(toPreview), this.fail());
  }

  execute(id: string, request: ImportRequest, idempotencyKey: string): Observable<ImportResult> {
    return this.http
      .post<{ id: string; status: string; counts: CountsDto }>(`${this.baseUrl}${id}/execute/`, {
        ...toBody(request),
        idempotency_key: idempotencyKey,
      })
      .pipe(
        map((dto): ImportResult => ({ id: dto.id, status: dto.status, counts: toCounts(dto.counts) })),
        this.fail(),
      );
  }

  list(page = 1): Observable<Page<ImportRunSummary>> {
    const params = new HttpParams().set('page', String(page));
    return this.http.get<Page<RunDto>>(this.baseUrl, { params }).pipe(
      map((p): Page<ImportRunSummary> => ({ ...p, results: p.results.map(toRun) })),
      this.fail(),
    );
  }

  get(id: string): Observable<ImportRunDetail> {
    return this.http.get<RunDto>(`${this.baseUrl}${id}/`).pipe(
      map((dto): ImportRunDetail => ({ ...toRun(dto), options: dto.options ?? {} })),
      this.fail(),
    );
  }

  rows(id: string, status: ImportRowStatus | '' = '', page = 1): Observable<Page<ImportRow>> {
    let params = new HttpParams().set('page', String(page));
    if (status) params = params.set('status', status);
    return this.http.get<Page<RowDto>>(`${this.baseUrl}${id}/rows/`, { params }).pipe(
      map((p): Page<ImportRow> => ({ ...p, results: p.results.map(toRow) })),
      this.fail(),
    );
  }

  template(): Observable<Blob> {
    return this.http.get(`${this.baseUrl}template/`, { responseType: 'blob' }).pipe(this.fail());
  }

  private fail<T>(): (source: Observable<T>) => Observable<T> {
    return (source) => source.pipe(catchError((err: HttpErrorResponse) => throwError(() => toApiError(err))));
  }
}
