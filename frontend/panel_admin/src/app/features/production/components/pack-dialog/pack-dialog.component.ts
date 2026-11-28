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
  unit: string;
}

/** Cantidad de bolsa por pack: positiva, hasta 4 decimales (igual que el servidor). */
function bagLength(control: AbstractControl): ValidationErrors | null {
  const value: unknown = control.value;
  const valid = typeof value === 'number' && value > 0 && value <= 9999.9999 && Math.abs(value * 10000 - Math.round(value * 10000)) < 1e-6;
  return valid ? null : { bagPerPack: true };
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
  serverErrors: { packs?: string; packProductId?: string; bagProductId?: string; bagPerPack?: string; labelProductId?: string } = {};
  readonly quantity = formatQuantity;

  readonly form = this.fb.nonNullable.group({
    packProductId: ['', Validators.required],
    bagProductId: ['', Validators.required],
    bagPerPack: [0.17, [Validators.required, bagLength]],
    labelProductId: [''],
    packs: [1, [Validators.required, wholeNumber]],
  });

  ngOnInit(): void {
    this.form.controls.bagPerPack.setValue(Number(this.order.packing?.suggestedBagPerPack ?? '0.17'));
    this.products.list({ active: true, pageSize: 100 }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: page => this.options = page.results.filter(product => product.tracksStock && product.id !== this.order.resultProduct.id)
        .map(product => ({ id: product.id, name: product.name, unit: product.baseUnit?.abbreviation ?? '' })),
      error: () => this.loadError = tr('PRODUCTION.ORDERS.PACK.LOAD_ERROR'),
    });
  }

  get unitsPerPack(): number { return this.order.packing?.unitsPerPack ?? 6; }
  get bagUnit(): string { return this.options.find(option => option.id === this.form.controls.bagProductId.value)?.unit ?? ''; }
  /** Bolsa total del empaque (cantidad por pack × packs), redondeada a 4 decimales. */
  get bagsTotal(): string {
    const per = this.form.controls.bagPerPack;
    return per.valid ? formatQuantity((Math.round(this.packs * per.value * 10000) / 10000).toFixed(4)) : '0';
  }
  get labelsPerPack(): number { return this.order.packing?.labelsPerPack ?? 1; }
  get packs(): number { const value = this.form.controls.packs.value; return this.form.controls.packs.valid ? value : 0; }
  get unit(): string { return this.order.resultProduct.unit?.abbreviation ?? ''; }

  get summary(): string {
    return tr('PRODUCTION.ORDERS.PACK.SUMMARY', {
      bulk: this.packs * this.unitsPerPack, unit: this.unit, lot: this.order.lot?.code ?? '',
      bags: `${this.bagsTotal} ${this.bagUnit}`.trim(), packs: this.packs,
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
      bagPerPack: value.bagPerPack, labelProductId: value.labelProductId || null,
    }).pipe(finalize(() => this.saving = false), takeUntilDestroyed(this.destroyRef)).subscribe({
      next: order => this.modal.close(order),
      error: (error: OrderApiError) => {
        this.shortages = error.shortages;
        this.serverErrors = { packs: error.fields.packs, packProductId: error.fields.packProductId, bagProductId: error.fields.bagProductId, bagPerPack: error.fields.bagPerPack,
          labelProductId: error.fields.labelProductId };
        this.error = error.shortages.length || error.status === 400 ? '' : error.message;
      },
    });
  }
}
