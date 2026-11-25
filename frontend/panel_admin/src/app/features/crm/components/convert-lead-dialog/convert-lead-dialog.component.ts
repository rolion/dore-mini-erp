import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { CrmApiError } from '../../models/board';
import { CrmContact } from '../../models/lead';
import { CrmLeadsApiService } from '../../services/crm-leads-api.service';

/** Prospecto que se convierte: basta con su id, nombre y teléfono (sirve desde la lista y desde una tarjeta). */
export type ConvertibleLead = CrmContact;

/**
 * Convierte un prospecto en cliente. El servidor vincula al único cliente con el mismo teléfono o crea uno; si hay
 * varios coincidentes responde 409 `multiple_customer_matches` y aquí se pide elegir uno. Se cierra con la conversión.
 */
@Component({
  selector: 'app-crm-convert-lead-dialog',
  templateUrl: './convert-lead-dialog.component.html',
  imports: [TranslatePipe, ReactiveFormsModule],
})
export class ConvertLeadDialogComponent {
  readonly choice = inject(FormBuilder).nonNullable.control('');

  lead!: ConvertibleLead;
  candidates: CrmContact[] = [];
  saving = false;
  errorMessage = '';
  /** 409 que no es de coincidencias (p. ej. el prospecto cambió): se muestra como aviso. */
  conflict = false;

  readonly activeModal = inject(NgbActiveModal);
  private api = inject(CrmLeadsApiService);
  private destroyRef = inject(DestroyRef);

  open(lead: ConvertibleLead): void {
    this.lead = lead;
  }

  get choosing(): boolean {
    return this.candidates.length > 0;
  }

  get canConfirm(): boolean {
    return !this.saving && (!this.choosing || !!this.choice.value);
  }

  confirm(): void {
    if (!this.canConfirm) {
      return;
    }
    this.saving = true;
    this.errorMessage = '';
    this.conflict = false;
    const customerId = this.choosing ? this.choice.value : undefined;
    this.api.convert(this.lead.id, customerId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (result) => {
        this.saving = false;
        this.activeModal.close(result);
      },
      error: (err: CrmApiError) => {
        this.saving = false;
        if (err.code === 'multiple_customer_matches' && err.candidates.length) {
          this.candidates = err.candidates;
          this.choice.setValue('');
          return;
        }
        this.conflict = err.status === 409;
        this.errorMessage = err.fieldErrors['customerId'] ?? err.message;
      },
    });
  }
}
