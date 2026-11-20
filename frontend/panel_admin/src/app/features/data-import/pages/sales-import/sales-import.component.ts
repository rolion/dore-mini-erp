import { tr } from '../../../../core/i18n/translate';
import { Component, DestroyRef, ElementRef, OnInit, inject, viewChild } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { NgbModal, NgbPagination } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { EMPTY, Subscription, catchError, switchMap, takeWhile, tap, timer } from 'rxjs';
import { PostingIssuesAlertComponent } from '../../../../shared/components/posting-issues-alert/posting-issues-alert.component';
import { PostingIssue } from '../../../../shared/models/receivable';
import { ImportConfirmDialogComponent } from '../../components/confirm-dialog/confirm-dialog.component';
import { ImportCountsComponent } from '../../components/import-counts/import-counts.component';
import { ImportRowsComponent } from '../../components/import-rows/import-rows.component';
import {
  DATE_FORMAT_OPTIONS,
  IMPORT_FIELDS,
  ImportApiError,
  ImportCapabilities,
  ImportField,
  ImportMapping,
  ImportOptions,
  ImportPreview,
  ImportRequest,
  ImportResult,
  ImportUpload,
  PAYMENT_METHOD_OPTIONS,
  PRODUCT_CATEGORY_OPTIONS,
  SALES_CHANNEL_OPTIONS,
  isActiveRun,
  newUuid,
} from '../../models/sales-import';
import { SalesImportApiService } from '../../services/sales-import-api.service';

export type ImportStep = 1 | 2 | 3 | 4;

export const PROBLEMS_PAGE_SIZE = 10;

/** Cada cuántos milisegundos se consulta el avance de una importación en segundo plano. */
export const POLL_INTERVAL_MS = 3000;

/** Asistente «Importar ventas»: Subir archivo → Mapear → Vista previa → Resultado (la carga no se deshace en bloque). */
@Component({
  selector: 'app-sales-import',
  templateUrl: './sales-import.component.html',
  imports: [
    TranslatePipe,
    ReactiveFormsModule,
    RouterLink,
    NgbPagination,
    PostingIssuesAlertComponent,
    ImportCountsComponent,
    ImportRowsComponent,
  ],
})
export class SalesImportComponent implements OnInit {
  readonly fields = IMPORT_FIELDS;
  readonly dateFormats = DATE_FORMAT_OPTIONS;
  readonly problemsPageSize = PROBLEMS_PAGE_SIZE;
  readonly stepDefs: readonly { n: ImportStep; labelKey: string }[] = [
    { n: 1, labelKey: 'DATA_IMPORT.STEP_UPLOAD' },
    { n: 2, labelKey: 'DATA_IMPORT.STEP_MAP' },
    { n: 3, labelKey: 'DATA_IMPORT.STEP_PREVIEW' },
    { n: 4, labelKey: 'DATA_IMPORT.STEP_RESULT' },
  ];

  private readonly fb = inject(FormBuilder).nonNullable;
  private readonly api = inject(SalesImportApiService);
  private readonly modal = inject(NgbModal);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly heading = viewChild<ElementRef<HTMLElement>>('stepHeading');

  step: ImportStep = 1;

  // Paso 1
  selectedFile: File | null = null;
  uploading = false;
  uploadErrors: string[] = [];
  templateError = false;
  /** Se está retomando una importación desde `?run=`. */
  resuming = false;

  // Paso 2
  upload: ImportUpload | null = null;
  readonly mapping: FormGroup<Record<ImportField, FormControl<string>>> = this.buildMappingGroup();
  readonly options = this.fb.group({
    inferProducts: [true],
    inferCustomers: [true],
    inferInventory: [true],
    inferAccounting: [true],
    defaultPaymentMethod: this.fb.control<ImportOptions['defaultPaymentMethod']>('CASH'),
    defaultSalesChannel: this.fb.control<ImportOptions['defaultSalesChannel']>('OTHER'),
    defaultCategory: this.fb.control<ImportOptions['defaultCategory']>('finished'),
    warehouseId: [''],
    dateFormat: this.fb.control<ImportOptions['dateFormat']>('dmy'),
  });
  previewing = false;
  previewErrors: string[] = [];

  // Paso 3
  preview: ImportPreview | null = null;
  problemsPage = 1;
  private previewSnapshot = '';
  executing = false;
  executeError: ImportApiError | null = null;
  postingIssues: PostingIssue[] = [];

  // Paso 4
  result: ImportResult | null = null;
  resumeError = '';
  /** La última consulta del avance falló; se sigue intentando. */
  pollError = false;
  private polling: Subscription | null = null;

  /** Clave de idempotencia: se genera al abrir el asistente y se reenvía en cada intento de carga. */
  private idempotencyKey = newUuid();

  private buildMappingGroup(): FormGroup<Record<ImportField, FormControl<string>>> {
    const controls = {} as Record<ImportField, FormControl<string>>;
    for (const field of IMPORT_FIELDS) {
      controls[field.key] = new FormControl('', { nonNullable: true });
    }
    return new FormGroup(controls);
  }

  ngOnInit(): void {
    const runId = this.route.snapshot.queryParamMap.get('run');
    if (runId) {
      this.resume(runId);
    }
  }

  // --- Retomar ---------------------------------------------------------------------------------------------------

  private resume(runId: string): void {
    this.resuming = true;
    this.api
      .get(runId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (run) => {
          this.resuming = false;
          if (run.status === 'COMPLETED' || run.status === 'FAILED' || isActiveRun(run.status)) {
            this.result = this.toResult(run);
            this.goTo(4);
            if (isActiveRun(run.status)) {
              this.watch(run.id);
            }
          } else {
            this.resumeError = tr('DATA_IMPORT.RESUME_UNAVAILABLE');
          }
        },
        error: (err: ImportApiError) => {
          this.resuming = false;
          this.resumeError = err.message;
        },
      });
  }

  // --- Paso 1: subir ---------------------------------------------------------------------------------------------

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.selectedFile = input.files?.item(0) ?? null;
    this.uploadErrors = [];
  }

  uploadFile(): void {
    if (!this.selectedFile || this.uploading) {
      return;
    }
    this.uploading = true;
    this.uploadErrors = [];
    this.api
      .upload(this.selectedFile)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (upload) => {
          this.uploading = false;
          this.applyUpload(upload);
        },
        error: (err: ImportApiError) => {
          this.uploading = false;
          this.uploadErrors = err.fieldMessages.length ? err.fieldMessages : [err.message];
        },
      });
  }

  private applyUpload(upload: ImportUpload): void {
    this.upload = upload;
    this.idempotencyKey = newUuid();
    this.preview = null;
    this.result = null;
    this.previewSnapshot = '';
    this.previewErrors = [];
    for (const field of IMPORT_FIELDS) {
      this.mapping.controls[field.key].setValue(upload.suggestedMapping[field.key] ?? '');
    }
    const caps = upload.capabilities;
    this.options.patchValue({
      inferProducts: true,
      inferCustomers: caps.customers,
      inferInventory: this.inventoryAvailable(caps),
      inferAccounting: caps.accounting,
      defaultPaymentMethod: 'CASH',
      defaultSalesChannel: 'OTHER',
      defaultCategory: 'finished',
      warehouseId: this.defaultWarehouse(caps),
      dateFormat: 'dmy',
    });
    this.setEnabled(this.options.controls.inferCustomers, caps.customers);
    this.setEnabled(this.options.controls.inferInventory, this.inventoryAvailable(caps));
    this.setEnabled(this.options.controls.inferAccounting, caps.accounting);
    void this.router.navigate([], { relativeTo: this.route, queryParams: { run: upload.id }, replaceUrl: true });
    this.goTo(2);
  }

  private setEnabled(control: FormControl<boolean>, enabled: boolean): void {
    if (enabled) {
      control.enable();
    } else {
      control.setValue(false);
      control.disable();
    }
  }

  private inventoryAvailable(caps: ImportCapabilities): boolean {
    return caps.inventory && caps.purchases;
  }

  private defaultWarehouse(caps: ImportCapabilities): string {
    if (!caps.inventory || caps.warehouses.length === 0) {
      return '';
    }
    if (caps.warehouses.length === 1) {
      return caps.warehouses[0].id;
    }
    return (caps.warehouses.find((w) => w.isDefault) ?? caps.warehouses[0]).id;
  }

  downloadTemplate(): void {
    this.templateError = false;
    this.api
      .template()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (blob) => {
          const url = URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = url;
          link.download = 'plantilla-ventas.csv';
          link.click();
          URL.revokeObjectURL(url);
        },
        error: () => (this.templateError = true),
      });
  }

  // --- Paso 2: mapear --------------------------------------------------------------------------------------------

  get capabilities(): ImportCapabilities | null {
    return this.upload?.capabilities ?? null;
  }

  get customersAvailable(): boolean {
    return !!this.capabilities?.customers;
  }

  get inventoryOptionAvailable(): boolean {
    return !!this.capabilities && this.inventoryAvailable(this.capabilities);
  }

  get accountingAvailable(): boolean {
    return !!this.capabilities?.accounting;
  }

  get paymentOptions() {
    const allowed = this.capabilities?.paymentMethods ?? [];
    const options = PAYMENT_METHOD_OPTIONS.filter((o) => allowed.includes(o.value));
    return options.length ? options : PAYMENT_METHOD_OPTIONS;
  }

  readonly categoryOptions = PRODUCT_CATEGORY_OPTIONS;

  get channelOptions() {
    const allowed = this.capabilities?.salesChannels ?? [];
    const options = SALES_CHANNEL_OPTIONS.filter((o) => allowed.includes(o.value));
    return options.length ? options : SALES_CHANNEL_OPTIONS;
  }

  samples(field: ImportField): string[] {
    const upload = this.upload;
    const column = this.mapping.controls[field].value;
    if (!upload || !column) {
      return [];
    }
    const index = upload.headers.indexOf(column);
    return index < 0 ? [] : upload.sampleRows.slice(0, 3).map((row) => row[index] ?? '');
  }

  get missingRequired(): boolean {
    return IMPORT_FIELDS.some((f) => f.required && !this.mapping.controls[f.key].value);
  }

  get canReview(): boolean {
    return !!this.upload && !this.missingRequired && !this.previewing;
  }

  private request(): ImportRequest {
    const mapping = {} as ImportMapping;
    for (const field of IMPORT_FIELDS) {
      mapping[field.key] = this.mapping.controls[field.key].value || null;
    }
    const raw = this.options.getRawValue();
    return {
      mapping,
      options: { ...raw, warehouseId: this.capabilities?.inventory && raw.warehouseId ? raw.warehouseId : null },
    };
  }

  review(): void {
    if (!this.canReview || !this.upload) {
      return;
    }
    this.previewing = true;
    this.previewErrors = [];
    const request = this.request();
    this.api
      .preview(this.upload.id, request)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (preview) => {
          this.previewing = false;
          this.preview = preview;
          this.previewSnapshot = JSON.stringify(request);
          this.problemsPage = 1;
          this.executeError = null;
          this.postingIssues = [];
          this.goTo(3);
        },
        error: (err: ImportApiError) => {
          this.previewing = false;
          this.previewErrors = err.fieldMessages.length ? err.fieldMessages : [err.message];
        },
      });
  }

  // --- Paso 3: vista previa --------------------------------------------------------------------------------------

  /** El mapeo u opciones cambiaron desde la última previsualización. */
  get stale(): boolean {
    return !!this.preview && this.previewSnapshot !== JSON.stringify(this.request());
  }

  get canExecute(): boolean {
    return !!this.preview && this.preview.toCreate > 0 && !this.stale && !this.executing;
  }

  get pagedProblems() {
    const start = (this.problemsPage - 1) * PROBLEMS_PAGE_SIZE;
    return this.preview?.problems.slice(start, start + PROBLEMS_PAGE_SIZE) ?? [];
  }

  backToEdit(): void {
    this.goTo(2);
  }

  execute(): void {
    if (!this.canExecute || !this.preview) {
      return;
    }
    const ref = this.modal.open(ImportConfirmDialogComponent, { backdrop: 'static', keyboard: false });
    (ref.componentInstance as ImportConfirmDialogComponent).salesToCreate = this.preview.toCreate;
    ref.result.then(
      () => this.runExecute(),
      () => undefined,
    );
  }

  /** Envía la carga; los reintentos reutilizan la misma clave de idempotencia. */
  runExecute(): void {
    if (this.executing || !this.upload) {
      return;
    }
    this.executing = true;
    this.executeError = null;
    this.postingIssues = [];
    this.api
      .execute(this.upload.id, this.request(), this.idempotencyKey)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          this.executing = false;
          this.result = result;
          this.goTo(4);
          if (isActiveRun(result.status)) {
            this.watch(result.id);
          }
        },
        error: (err: ImportApiError) => {
          this.executing = false;
          this.executeError = err;
          this.postingIssues = err.code === 'posting_configuration_missing' ? err.issues : [];
        },
      });
  }

  private toResult(run: ImportResult): ImportResult {
    return {
      id: run.id,
      status: run.status,
      counts: run.counts,
      processed: run.processed,
      total: run.total,
      failure: run.failure,
    };
  }

  /** Consulta el avance cada pocos segundos hasta que la importación termina; se corta al salir de la página. */
  private watch(runId: string): void {
    this.polling?.unsubscribe();
    this.pollError = false;
    this.polling = timer(POLL_INTERVAL_MS, POLL_INTERVAL_MS)
      .pipe(
        switchMap(() =>
          this.api.get(runId).pipe(
            catchError(() => {
              this.pollError = true;
              return EMPTY;
            }),
          ),
        ),
        tap((run) => {
          this.pollError = false;
          this.result = this.toResult(run);
        }),
        takeWhile((run) => isActiveRun(run.status)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe();
  }

  get inProgress(): boolean {
    return !!this.result && isActiveRun(this.result.status);
  }

  get progressPercent(): number {
    const r = this.result;
    return r && r.total > 0 ? Math.min(100, Math.round((r.processed / r.total) * 100)) : 0;
  }

  /** Vuelve a la vista previa para reintentar una importación que se detuvo (lo ya cargado no se duplica). */
  retry(): void {
    this.polling?.unsubscribe();
    this.result = null;
    this.executeError = null;
    this.goTo(3);
  }

  get isRunning(): boolean {
    return this.executeError?.code === 'import_running';
  }

  get isConfigMissing(): boolean {
    return this.executeError?.code === 'posting_configuration_missing';
  }

  // --- Paso 4 y navegación ---------------------------------------------------------------------------------------

  get hasFailures(): boolean {
    return !!this.result && (this.result.status === 'FAILED' || this.result.counts.failed > 0);
  }

  restart(): void {
    this.polling?.unsubscribe();
    this.pollError = false;
    this.upload = null;
    this.preview = null;
    this.result = null;
    this.selectedFile = null;
    this.previewSnapshot = '';
    this.uploadErrors = [];
    this.previewErrors = [];
    this.executeError = null;
    this.postingIssues = [];
    this.resumeError = '';
    this.idempotencyKey = newUuid();
    void this.router.navigate([], { relativeTo: this.route, queryParams: {}, replaceUrl: true });
    this.goTo(1);
  }

  private goTo(step: ImportStep): void {
    this.step = step;
    setTimeout(() => this.heading()?.nativeElement.focus());
  }
}
