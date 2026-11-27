import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { NgSelectComponent } from '@ng-select/ng-select';
import { TranslatePipe } from '@ngx-translate/core';
import { finalize } from 'rxjs';
import { tr } from '../../../../core/i18n/translate';
import { ProductsApiService } from '../../../products/services/products-api.service';
import { MAX_PACKS, OrderApiError, OrderShortage, ProductionOrder } from '../../models/order';
import { formatQuantity } from '../../models/recipe';
import { OrdersApiService } from '../../services/orders-api.service';

export interface ProductOption {
  id: string;
  name: string;
}

function wholeNumber(control: AbstractControl): ValidationErrors | null {
  const value: unknown = control.value;
  return typeof value === 'number' && Number.isInteger(value) && value >= 1 && value <= MAX_PACKS ? null : { packs: true };
}

/** Diálogo «Registrar empaque» (DDR-empacar-bolsas-de-6-venta-detalle-registrar-empaque). */
@Component({
  selector: 'app-pack-dialog',
  imports: [TranslatePipe, ReactiveFormsModule, NgSelectComponent],
  templateUrl: './pack-dialog.component.html',
})
export class PackDialogComponent implements OnInit {
  readonly modal = inject(NgbActiveModal);
  private api = inject(OrdersApiService);
  private products = inject(ProductsApiService);
  private destroyRef = inject(DestroyRef);
  private fb = inject(FormBuilder);

  /** La orden lista para empacar; la asigna quien abre el diálogo. */
  order!: ProductionOrder;
  /** Un intento = un `request_id`: el doble clic o el reintento no duplican el empaque. */
  readonly requestId = crypto.randomUUID();
  options: ProductOption[] = [];
  loadError = '';
  saving = false;
  submitted = false;
  error = '';
  shortages: OrderShortage[] = [];
  serverErrors: { packs?: string; packProductId?: string; bagProductId?: string; labelProductId?: string } = {};
  readonly quantity = formatQuantity;

  readonly form = this.fb.nonNullable.group({
    packProductId: ['', Validators.required],
    bagProductId: ['', Validators.required],
    labelProductId: [''],
    packs: [1, [Validators.required, wholeNumber]],
  });

  ngOnInit(): void {
    this.products.list({ active: true, pageSize: 100 }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: page => this.options = page.results.filter(product => product.tracksStock && product.id !== this.order.resultProduct.id)
        .map(product => ({ id: product.id, name: product.name })),
      error: () => this.loadError = tr('PRODUCTION.ORDERS.PACK.LOAD_ERROR'),
    });
  }

  get unitsPerPack(): number { return this.order.packing?.unitsPerPack ?? 6; }
  get bagsPerPack(): number { return this.order.packing?.bagsPerPack ?? 1; }
  get labelsPerPack(): number { return this.order.packing?.labelsPerPack ?? 1; }
  get packs(): number { const value = this.form.controls.packs.value; return this.form.controls.packs.valid ? value : 0; }
  get unit(): string { return this.order.resultProduct.unit?.abbreviation ?? ''; }

  get summary(): string {
    return tr('PRODUCTION.ORDERS.PACK.SUMMARY', {
      bulk: this.packs * this.unitsPerPack, unit: this.unit, lot: this.order.lot?.code ?? '',
      bags: this.packs * this.bagsPerPack, packs: this.packs,
      labels: this.form.controls.labelProductId.value
        ? tr('PRODUCTION.ORDERS.PACK.SUMMARY_LABELS', { labels: this.packs * this.labelsPerPack }) : '' });
  }

  shortageText(item: OrderShortage): string {
    return tr('PRODUCTION.ORDERS.PACK.SHORTAGE_LINE', {
      name: item.productName, requested: formatQuantity(item.requested), available: formatQuantity(item.available),
      missing: formatQuantity(item.missing) });
  }

  submit(): void {
    this.submitted = true;
    this.error = '';
    this.shortages = [];
    this.serverErrors = {};
    if (this.saving || this.form.invalid) return;
    const value = this.form.getRawValue();
    this.saving = true;
    this.api.pack(this.order.id, {
      requestId: this.requestId, packs: value.packs, packProductId: value.packProductId, bagProductId: value.bagProductId,
      labelProductId: value.labelProductId || null,
    }).pipe(finalize(() => this.saving = false), takeUntilDestroyed(this.destroyRef)).subscribe({
      next: order => this.modal.close(order),
      error: (error: OrderApiError) => {
        this.shortages = error.shortages;
        this.serverErrors = { packs: error.fields.packs, packProductId: error.fields.packProductId, bagProductId: error.fields.bagProductId,
          labelProductId: error.fields.labelProductId };
        this.error = error.shortages.length || error.status === 400 ? '' : error.message;
      },
    });
  }
}
