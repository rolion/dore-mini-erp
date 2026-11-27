import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormArray, FormControl, FormGroup, ReactiveFormsModule, ValidationErrors } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { finalize } from 'rxjs';
import { HasUnsavedChanges } from '../../../../core/guard/unsaved-changes.guard';
import { tr } from '../../../../core/i18n/translate';
import { OrderApiError, OrderFieldErrors, OrderShortage, ProductionOrder, formatOrderNumber, toScaled } from '../../models/order';
import { formatQuantity } from '../../models/recipe';
import { OrdersApiService } from '../../services/orders-api.service';

/** Cantidad decimal con hasta 4 decimales; el cero solo se admite si `allowZero`. */
export function quantityValidator(allowZero: boolean) {
  return (control: AbstractControl): ValidationErrors | null => {
    const value = String(control.value ?? '').trim();
    if (!value) return { required: true };
    const scaled = toScaled(value);
    if (scaled === null) return { quantity: true };
    return !allowZero && scaled === 0n ? { quantity: true } : null;
  };
}

/** `yyyy-MM-ddTHH:mm` en hora local, como espera `datetime-local`. */
export function toLocalInput(date: Date): string {
  const pad = (n: number): string => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

@Component({
  selector: 'app-order-refrigerate',
  imports: [TranslatePipe, ReactiveFormsModule, RouterLink],
  templateUrl: './order-refrigerate.component.html',
  styleUrl: './order-refrigerate.component.scss',
})
export class OrderRefrigerateComponent implements OnInit, HasUnsavedChanges {
  private api = inject(OrdersApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);

  readonly orderId = this.route.snapshot.paramMap.get('id') ?? '';
  readonly form = new FormGroup({
    enteredAt: new FormControl(toLocalInput(new Date()), { nonNullable: true, validators: [quantityLike] }),
    actualOutput: new FormControl('', { nonNullable: true, validators: [quantityValidator(false)] }),
    lines: new FormArray<FormControl<string>>([]),
  });
  order: ProductionOrder | null = null;
  loading = true;
  saving = false;
  submitted = false;
  error = '';
  server: OrderFieldErrors = {};
  shortages: OrderShortage[] = [];
  readonly quantity = formatQuantity;
  readonly number = formatOrderNumber;

  ngOnInit(): void {
    this.api.get(this.orderId).pipe(finalize(() => this.loading = false), takeUntilDestroyed(this.destroyRef)).subscribe({
      next: order => this.load(order),
      error: (error: OrderApiError) => this.error = error.message,
    });
  }

  private load(order: ProductionOrder): void {
    if (order.status !== 'in_preparation') {
      void this.router.navigate(['/pocketbiz/production/orders', order.id]);
      return;
    }
    this.order = order;
    this.form.controls.actualOutput.setValue(formatQuantity(order.expectedOutput));
    for (const line of order.ingredients) {
      this.form.controls.lines.push(new FormControl(formatQuantity(line.expectedQuantity), { nonNullable: true, validators: [quantityValidator(true)] }));
    }
    this.form.markAsPristine();
  }

  hasUnsavedChanges(): boolean { return this.form.dirty && !this.saving; }

  shortageOf(productId: string): OrderShortage | undefined {
    return this.shortages.find(item => item.productId === productId);
  }

  lineInvalid(index: number): boolean {
    return this.submitted && this.form.controls.lines.at(index).invalid;
  }

  submit(): void {
    const order = this.order;
    if (!order || this.saving) return;
    this.submitted = true;
    this.server = {};
    this.shortages = [];
    this.error = '';
    if (this.form.invalid) return;
    const value = this.form.getRawValue();
    const when = new Date(value.enteredAt);
    if (Number.isNaN(when.getTime())) return;
    this.saving = true;
    this.api.refrigerate(order.id, {
      enteredAt: when.toISOString(),
      actualOutput: value.actualOutput.trim(),
      ingredients: order.ingredients.map((line, index) => ({ productId: line.productId, actualQuantity: value.lines[index].trim() })),
    }).pipe(finalize(() => this.saving = false), takeUntilDestroyed(this.destroyRef)).subscribe({
      next: done => {
        this.form.markAsPristine();
        void this.router.navigate(['/pocketbiz/production/orders', done.id]);
      },
      error: (error: OrderApiError) => {
        this.server = error.fields;
        this.shortages = error.shortages;
        this.error = error.shortages.length ? tr('PRODUCTION.ORDERS.REFRIGERATE.SHORTAGE_ALERT') : error.fields.detail ?? error.message;
      },
    });
  }
}

function quantityLike(control: AbstractControl): ValidationErrors | null {
  return String(control.value ?? '').trim() ? null : { required: true };
}
