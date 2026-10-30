import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormArray, FormBuilder, FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { finalize, forkJoin } from 'rxjs';
import { HasUnsavedChanges } from '../../../../core/guard/unsaved-changes.guard';
import { Purchase, PurchaseApiError, todayIso } from '../../models/purchase';
import {
  ReceiptApiError,
  ReceiptFieldErrors,
  ReceiptLineInput,
  ReceptionForm,
  ReceptionFormLine,
} from '../../models/receipt';
import { PurchasesApiService } from '../../services/purchases-api.service';
import {
  isPositive,
  isReceivable,
  pendingAfter,
  positiveQuantity,
  quantityError,
} from '../../services/reception-quantities';
import { ReceiptsApiService } from '../../services/receipts-api.service';

export const NO_POSITIVE_MESSAGE = 'Indica una cantidad mayor a cero en al menos un producto.';
export const FUTURE_DATE_MESSAGE = 'La fecha de recepción no puede ser futura.';
export const DATE_REQUIRED_MESSAGE = 'La fecha de recepción es obligatoria.';
export const WAREHOUSE_REQUIRED_MESSAGE = 'Selecciona un almacén para los productos con control de stock.';

/** Línea del resumen: lo que se recibe y lo que queda pendiente después. */
export interface ReviewLine {
  line: ReceptionFormLine;
  quantity: string;
  pendingAfter: string;
}

/** Formulario de recepción en dos pasos (editar → resumen); el servidor repite cada regla al confirmar. */
@Component({
  selector: 'app-reception-form',
  templateUrl: './reception-form.component.html',
  imports: [ReactiveFormsModule, RouterLink, DatePipe],
})
export class ReceptionFormComponent implements OnInit, HasUnsavedChanges {
  private fb = inject(FormBuilder);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toastr = inject(ToastrService);
  private purchasesApi = inject(PurchasesApiService);
  private receiptsApi = inject(ReceiptsApiService);
  private destroyRef = inject(DestroyRef);

  readonly today = todayIso();
  /** Identificador de la recepción: se reutiliza en cada reintento para no duplicarla. */
  private readonly receiptId = crypto.randomUUID();
  purchaseId = '';
  purchase: Purchase | null = null;
  reception: ReceptionForm | null = null;
  loading = true;
  loadError = '';
  step: 'edit' | 'review' = 'edit';
  submitting = false;
  submitted = false;
  /** Aviso de negocio del servidor (409): se conserva lo escrito. */
  conflictMessage = '';
  serverErrors: ReceiptFieldErrors = { lines: [] };
  /** Posición en `reception.lines` de cada línea enviada, para ubicar los errores del servidor. */
  private sentRows: number[] = [];

  readonly form = this.fb.nonNullable.group({
    receiptDate: [todayIso(), [Validators.required]],
    warehouseId: [''],
    quantities: this.fb.array<FormControl<string>>([]),
  });

  get quantities(): FormArray<FormControl<string>> {
    return this.form.controls.quantities;
  }

  ngOnInit(): void {
    this.purchaseId = this.route.snapshot.paramMap.get('id') ?? '';
    this.load();
  }

  hasUnsavedChanges(): boolean {
    return !this.submitted && this.quantities.controls.some((control) => control.value.trim() !== '');
  }

  // --- derivados -------------------------------------------------------------------------------------------

  /** El almacén solo aplica con Inventario activo y algún producto controlado por recibir. */
  get showWarehouse(): boolean {
    const form = this.reception;
    return !!form && form.inventoryEnabled && form.lines.some((l) => l.tracksStock && isPositive(l.pending));
  }

  get noWarehouses(): boolean {
    return this.showWarehouse && (this.reception?.warehouses.length ?? 0) === 0;
  }

  /** Alguna línea controlada tiene cantidad por recibir: entonces el almacén es obligatorio. */
  get requiresWarehouse(): boolean {
    return this.reception?.lines.some((l, i) => l.tracksStock && this.isReceivableRow(i)) ?? false;
  }

  get selectedWarehouseName(): string {
    const id = this.form.controls.warehouseId.value;
    return this.reception?.warehouses.find((w) => w.id === id)?.name ?? '';
  }

  get receivableCount(): number {
    return this.quantities.controls.filter((control) => isReceivable(control.value)).length;
  }

  get hasPositive(): boolean {
    return this.receivableCount > 0;
  }

  get dateError(): string {
    const value = this.form.controls.receiptDate.value;
    if (!value) return DATE_REQUIRED_MESSAGE;
    if (value > this.today) return FUTURE_DATE_MESSAGE;
    return this.serverErrors.receiptDate ?? '';
  }

  get warehouseError(): string {
    if (this.serverErrors.warehouseId) return this.serverErrors.warehouseId;
    return this.requiresWarehouse && !this.form.controls.warehouseId.value ? WAREHOUSE_REQUIRED_MESSAGE : '';
  }

  /** Error de la línea: primero lo que se ve en el navegador, luego lo que respondió el servidor. */
  lineError(row: number): string {
    const line = this.reception?.lines[row];
    if (!line) return '';
    const local = quantityError(this.quantities.at(row).value, line.pending, line.allowsFractions);
    if (local) return local;
    const sent = this.sentRows.indexOf(row);
    return sent >= 0 ? (this.serverErrors.lines[sent]?.quantity ?? this.serverErrors.lines[sent]?.itemId ?? '') : '';
  }

  get hasLineErrors(): boolean {
    return this.quantities.controls.some((_, row) => !!this.lineError(row));
  }

  get canReview(): boolean {
    return (
      !this.loading &&
      this.hasPositive &&
      !this.hasLineErrors &&
      !this.dateError &&
      !this.warehouseError &&
      !(this.requiresWarehouse && this.noWarehouses)
    );
  }

  get reviewLines(): ReviewLine[] {
    const lines = this.reception?.lines ?? [];
    return lines.flatMap((line, row) => {
      const quantity = positiveQuantity(this.quantities.at(row).value);
      return quantity ? [{ line, quantity, pendingAfter: pendingAfter(line.pending, quantity) }] : [];
    });
  }

  get stockEntryCount(): number {
    return this.reviewLines.filter((l) => l.line.tracksStock).length;
  }

  isComplete(line: ReceptionFormLine): boolean {
    return !isPositive(line.pending);
  }

  // --- acciones --------------------------------------------------------------------------------------------

  fillAll(): void {
    this.reception?.lines.forEach((line, row) => {
      this.quantities.at(row).setValue(isPositive(line.pending) ? line.pending : '');
    });
    this.clearServerErrors();
  }

  onChange(): void {
    this.clearServerErrors();
  }

  review(): void {
    if (!this.canReview) {
      this.form.markAllAsTouched();
      return;
    }
    this.step = 'review';
  }

  backToEdit(): void {
    this.step = 'edit';
  }

  confirm(): void {
    if (this.submitting || !this.canReview) return;
    const lines: ReceiptLineInput[] = [];
    this.sentRows = [];
    this.reception?.lines.forEach((line, row) => {
      const quantity = positiveQuantity(this.quantities.at(row).value);
      if (quantity) {
        lines.push({ itemId: line.itemId, quantity });
        this.sentRows.push(row);
      }
    });
    this.submitting = true;
    this.conflictMessage = '';
    this.receiptsApi
      .create(this.purchaseId, {
        receiptId: this.receiptId,
        receiptDate: this.form.controls.receiptDate.value,
        warehouseId: this.requiresWarehouse ? this.form.controls.warehouseId.value || null : null,
        lines,
      })
      .pipe(
        finalize(() => (this.submitting = false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (receipt) => {
          this.submitted = true;
          this.toastr.success(`Recepción ${receipt.reference} registrada`);
          void this.router.navigate(['/pocketbiz/purchases', this.purchaseId], { queryParams: { tab: 'receptions' } });
        },
        error: (err: ReceiptApiError) => this.onSubmitError(err),
      });
  }

  // --- internos --------------------------------------------------------------------------------------------

  private isReceivableRow(row: number): boolean {
    return isReceivable(this.quantities.at(row).value);
  }

  private clearServerErrors(): void {
    this.serverErrors = { lines: [] };
    this.conflictMessage = '';
  }

  private onSubmitError(err: ReceiptApiError): void {
    if (err.status === 400) {
      this.serverErrors = err.fieldErrors;
      this.step = 'edit';
      this.toastr.error(err.fieldErrors.linesMessage ?? err.message);
    } else if (err.status === 409) {
      this.conflictMessage = err.message;
      this.step = 'edit';
      this.refreshLines();
    } else {
      this.toastr.error(err.message);
    }
  }

  /** Vuelve a leer los pendientes (otra recepción pudo cambiarlos) sin perder lo escrito. */
  private refreshLines(): void {
    this.receiptsApi
      .receptionForm(this.purchaseId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (form) => this.applyForm(form, true),
        error: () => undefined,
      });
  }

  private applyForm(form: ReceptionForm, keepValues: boolean): void {
    const previous = new Map(
      (this.reception?.lines ?? []).map((line, row) => [line.itemId, this.quantities.at(row)?.value ?? '']),
    );
    this.reception = form;
    this.quantities.clear();
    for (const line of form.lines) {
      this.quantities.push(new FormControl(keepValues ? (previous.get(line.itemId) ?? '') : '', { nonNullable: true }));
    }
    if (!this.form.controls.warehouseId.value && form.warehouseId) {
      this.form.controls.warehouseId.setValue(form.warehouseId);
    }
  }

  private load(): void {
    forkJoin({
      purchase: this.purchasesApi.get(this.purchaseId),
      reception: this.receiptsApi.receptionForm(this.purchaseId),
    })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: ({ purchase, reception }) => {
          this.purchase = purchase;
          this.applyForm(reception, false);
          this.loading = false;
        },
        error: (err: PurchaseApiError | ReceiptApiError) => {
          this.loading = false;
          this.loadError = err.message;
        },
      });
  }
}
