import { DatePipe } from '@angular/common';
import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { Observable } from 'rxjs';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import { CrmApiError } from '../../models/board';
import {
  CRM_LOST_REASON_MAX_LENGTH, CrmCloseResult, CrmLinkableOrder, CrmOpportunity, opportunityContact,
} from '../../models/opportunity';
import { CrmOpportunitiesApiService } from '../../services/crm-opportunities-api.service';

/** Motivo con el que se descarta el diálogo cuando la persona pide convertir el prospecto antes de vincular un pedido. */
export const CLOSE_DIALOG_CONVERT = 'convert';

/**
 * Cierra una oportunidad (patrón «Diálogo de acción irreversible con motivo»): ganada, con pedido opcional del mismo
 * cliente si Ventas está habilitado, o perdida con motivo obligatorio. Con una oportunidad ya ganada sin pedido, solo
 * vincula el pedido. Se cierra con la oportunidad que devuelve el servidor.
 */
@Component({
  selector: 'app-crm-close-opportunity-dialog',
  templateUrl: './close-opportunity-dialog.component.html',
  imports: [TranslatePipe, ReactiveFormsModule, MoneyPipe, DatePipe],
})
export class CloseOpportunityDialogComponent {
  readonly reasonMaxLength = CRM_LOST_REASON_MAX_LENGTH;
  private fb = inject(FormBuilder).nonNullable;
  readonly form = this.fb.group({
    result: this.fb.control<CrmCloseResult | ''>('', Validators.required),
    lostReason: ['', Validators.maxLength(CRM_LOST_REASON_MAX_LENGTH)],
    orderId: [''],
  });

  opportunity!: CrmOpportunity;
  salesEnabled = false;
  orders: CrmLinkableOrder[] = [];
  ordersLoading = false;
  ordersError = '';
  saving = false;
  errorMessage = '';
  /** El error mostrado es un 409 (regla de negocio): aviso en lugar de error. */
  conflict = false;
  reasonError = '';
  orderError = '';
  private ordersLoaded = false;

  readonly activeModal = inject(NgbActiveModal);
  private api = inject(CrmOpportunitiesApiService);
  private destroyRef = inject(DestroyRef);

  constructor() {
    this.form.controls.result.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((result) => {
      this.errorMessage = '';
      if (result === 'won') this.loadOrders();
    });
    this.form.controls.lostReason.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => (this.reasonError = ''));
  }

  open(opportunity: CrmOpportunity, salesEnabled: boolean): void {
    this.opportunity = opportunity;
    this.salesEnabled = salesEnabled;
    if (this.linkOnly) {
      this.form.controls.result.setValue('won');
    }
  }

  /** Oportunidad ya ganada sin pedido: el diálogo solo vincula el pedido. */
  get linkOnly(): boolean {
    return this.opportunity.status === 'won';
  }

  get contactName(): string {
    return opportunityContact(this.opportunity)?.name ?? '';
  }

  get result(): CrmCloseResult | '' {
    return this.form.controls.result.value;
  }

  /** Ganada sin cliente (solo prospecto): para vincular un pedido hay que convertirlo antes. */
  get needsConversion(): boolean {
    return this.salesEnabled && !this.opportunity.customer && !!this.opportunity.lead;
  }

  get showOrders(): boolean {
    return this.result === 'won' && this.salesEnabled && !!this.opportunity.customer;
  }

  get reasonLength(): number {
    return this.form.controls.lostReason.value.length;
  }

  get canConfirm(): boolean {
    if (this.saving || !this.result) return false;
    if (this.result === 'lost') {
      const reason = this.form.controls.lostReason.value.trim();
      return !!reason && reason.length <= CRM_LOST_REASON_MAX_LENGTH;
    }
    return !this.linkOnly || !!this.form.controls.orderId.value;
  }

  requestConversion(): void {
    this.activeModal.dismiss(CLOSE_DIALOG_CONVERT);
  }

  confirm(): void {
    if (!this.canConfirm) {
      return;
    }
    this.saving = true;
    this.errorMessage = '';
    this.conflict = false;
    this.reasonError = '';
    this.orderError = '';
    const value = this.form.getRawValue();
    const orderId = this.showOrders && value.orderId ? value.orderId : undefined;
    let request: Observable<CrmOpportunity>;
    if (this.linkOnly) {
      request = this.api.setOrder(this.opportunity.id, value.orderId);
    } else if (value.result === 'lost') {
      request = this.api.close(this.opportunity.id, { result: 'lost', lostReason: value.lostReason.trim() });
    } else {
      request = this.api.close(this.opportunity.id, { result: 'won', orderId });
    }
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (saved) => {
        this.saving = false;
        this.activeModal.close(saved);
      },
      error: (err: CrmApiError) => {
        this.saving = false;
        this.reasonError = err.fieldErrors['lostReason'] ?? '';
        this.orderError = err.fieldErrors['orderId'] ?? '';
        this.conflict = err.status === 409;
        this.errorMessage = this.reasonError || this.orderError ? '' : err.message;
      },
    });
  }

  private loadOrders(): void {
    if (this.ordersLoaded || !this.salesEnabled || !this.opportunity.customer) {
      return;
    }
    this.ordersLoaded = true;
    this.ordersLoading = true;
    this.ordersError = '';
    this.api.linkableOrders(this.opportunity.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (orders) => {
        this.ordersLoading = false;
        this.orders = orders;
      },
      error: (err: CrmApiError) => {
        this.ordersLoading = false;
        this.ordersLoaded = false;
        this.ordersError = err.message;
      },
    });
  }

  retryOrders(): void {
    this.loadOrders();
  }
}
