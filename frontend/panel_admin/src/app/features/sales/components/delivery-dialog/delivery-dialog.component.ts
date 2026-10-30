import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { EMPTY, catchError, finalize, switchMap, tap } from 'rxjs';
import {
  DeliveryLine,
  DeliveryPreview,
  Order,
  OrderApiError,
  OrderRuleError,
  formatQuantity,
  todayIso,
} from '../../models/order';
import { OrdersApiService } from '../../services/orders-api.service';

/** Motivo con el que se descarta el diálogo cuando el pedido cambió en el servidor y hay que recargarlo. */
export const STALE_ORDER = 'stale';

/**
 * Confirmación de la entrega de un pedido con productos que controlan stock: fecha, almacén de salida y el efecto
 * en las existencias. Los saldos son informativos; el servidor vuelve a validar al confirmar. Se cierra devolviendo
 * el pedido entregado.
 */
@Component({
  selector: 'app-delivery-dialog',
  templateUrl: './delivery-dialog.component.html',
  imports: [ReactiveFormsModule],
})
export class DeliveryDialogComponent {
  readonly today = todayIso();
  readonly form = inject(FormBuilder).nonNullable.group({
    deliveredDate: [todayIso(), Validators.required],
    warehouseId: [''],
  });
  readonly format = formatQuantity;

  /** Pedido y vista previa; los fija quien abre el diálogo. */
  order: Order | null = null;
  preview: DeliveryPreview | null = null;
  /** Se está recalculando la tabla (cambio de almacén o relectura tras un conflicto). */
  loadingLines = false;
  saving = false;
  /** Mensaje del servidor de la última confirmación fallida (el diálogo conserva lo elegido). */
  errorMessage = '';
  serverErrors: { deliveredDate?: string; warehouseId?: string } = {};

  readonly activeModal = inject(NgbActiveModal);
  private api = inject(OrdersApiService);
  private destroyRef = inject(DestroyRef);

  constructor() {
    this.form.controls.warehouseId.valueChanges
      .pipe(
        tap(() => {
          this.loadingLines = true;
          this.errorMessage = '';
          this.serverErrors = {};
        }),
        switchMap((warehouseId) => this.fetchPreview(warehouseId)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((preview) => {
        this.preview = preview;
        this.loadingLines = false;
      });
    this.form.controls.deliveredDate.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => (this.serverErrors = { ...this.serverErrors, deliveredDate: undefined }));
  }

  init(order: Order, preview: DeliveryPreview): void {
    this.order = order;
    this.preview = preview;
    this.form.patchValue({ warehouseId: preview.warehouseId ?? '' }, { emitEvent: false });
  }

  get noWarehouse(): boolean {
    return (this.preview?.warehouses.length ?? 0) === 0;
  }

  get singleWarehouse(): boolean {
    return (this.preview?.warehouses.length ?? 0) === 1;
  }

  get warehouseName(): string {
    const id = this.form.controls.warehouseId.value;
    return this.preview?.warehouses.find((w) => w.id === id)?.name ?? '';
  }

  /** Líneas cuyo saldo proyectado quedaría negativo. */
  get shortLines(): DeliveryLine[] {
    return (this.preview?.lines ?? []).filter((line) => line.insufficient);
  }

  /** Con la política de bloqueo vigente, una línea sin existencia impide confirmar. */
  get blocked(): boolean {
    return !!this.preview && !this.preview.allowNegativeStock && this.shortLines.length > 0;
  }

  get warnsNegative(): boolean {
    return !!this.preview?.allowNegativeStock && this.shortLines.length > 0;
  }

  get canConfirm(): boolean {
    return (
      !this.saving &&
      !this.loadingLines &&
      !this.noWarehouse &&
      this.form.valid &&
      !!this.form.controls.warehouseId.value &&
      !this.blocked
    );
  }

  confirm(): void {
    const order = this.order;
    if (!order || !this.canConfirm) return;
    const { deliveredDate, warehouseId } = this.form.getRawValue();
    this.saving = true;
    this.errorMessage = '';
    this.serverErrors = {};
    this.api
      .deliver(order.id, deliveredDate, warehouseId)
      .pipe(
        finalize(() => (this.saving = false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (delivered) => this.activeModal.close(delivered),
        error: (err: OrderApiError) => this.onError(err),
      });
  }

  private fetchPreview(warehouseId: string) {
    return this.api.deliveryPreview(this.order!.id, warehouseId || undefined).pipe(
      catchError((err: OrderApiError) => {
        this.errorMessage = err.message;
        this.loadingLines = false;
        return EMPTY;
      }),
    );
  }

  private onError(err: OrderApiError): void {
    if (err instanceof OrderRuleError && err.code === 'invalid_transition') {
      // Otra pestaña o persona ya cambió el pedido: no se puede entregar desde esta foto.
      this.activeModal.dismiss(STALE_ORDER);
      return;
    }
    if (err.status === 400 && Object.keys(err.fieldErrors).length) {
      this.serverErrors = {
        deliveredDate: err.fieldErrors.deliveredDate?.join(' '),
        warehouseId: err.fieldErrors.warehouseId?.join(' '),
      };
      return;
    }
    this.errorMessage = err.message;
    if (err instanceof OrderRuleError && err.code === 'insufficient_stock') {
      // Las existencias cambiaron desde que se abrió el diálogo: se muestran los valores vigentes.
      this.loadingLines = true;
      this.fetchPreview(this.form.controls.warehouseId.value)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe((preview) => {
          this.preview = preview;
          this.loadingLines = false;
        });
    }
  }
}
