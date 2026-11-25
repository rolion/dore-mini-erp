import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { CrmApiError } from '../../models/board';
import { CRM_LEAD_NAME_MAX_LENGTH, CrmLead } from '../../models/lead';
import { CrmLeadsApiService } from '../../services/crm-leads-api.service';

function notBlank(control: AbstractControl<string>): ValidationErrors | null {
  return control.value.trim() ? null : { required: true };
}

type LeadField = 'name' | 'phone' | 'email';

/** Alta o edición de un prospecto; se cierra devolviendo el prospecto guardado. */
@Component({
  selector: 'app-crm-lead-dialog',
  templateUrl: './lead-dialog.component.html',
  imports: [TranslatePipe, ReactiveFormsModule],
})
export class LeadDialogComponent {
  readonly nameMaxLength = CRM_LEAD_NAME_MAX_LENGTH;
  readonly form = inject(FormBuilder).nonNullable.group({
    name: ['', [notBlank, Validators.maxLength(CRM_LEAD_NAME_MAX_LENGTH)]],
    phone: ['', [Validators.maxLength(30)]],
    email: ['', [Validators.email, Validators.maxLength(254)]],
  });

  /** Prospecto que se edita; `null` para crear. */
  lead: CrmLead | null = null;
  saving = false;
  errorMessage = '';
  serverErrors: Partial<Record<LeadField, string>> = {};

  readonly activeModal = inject(NgbActiveModal);
  private api = inject(CrmLeadsApiService);
  private destroyRef = inject(DestroyRef);

  constructor() {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.serverErrors = {};
      this.errorMessage = '';
    });
  }

  edit(lead: CrmLead): void {
    this.lead = lead;
    this.form.setValue({ name: lead.name, phone: lead.phone, email: lead.email });
  }

  get isEdit(): boolean {
    return this.lead !== null;
  }

  invalid(field: LeadField): boolean {
    const control = this.form.controls[field];
    return (control.invalid && (control.touched || control.dirty)) || !!this.serverErrors[field];
  }

  onSubmit(): void {
    if (this.form.invalid || this.saving) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    const input = { name: value.name.trim(), phone: value.phone.trim(), email: value.email.trim() };
    this.saving = true;
    const request = this.lead ? this.api.update(this.lead.id, input) : this.api.create(input);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (saved) => {
        this.saving = false;
        this.activeModal.close(saved);
      },
      error: (err: CrmApiError) => {
        this.saving = false;
        this.serverErrors = { name: err.fieldErrors['name'], phone: err.fieldErrors['phone'], email: err.fieldErrors['email'] };
        const hasField = Object.values(this.serverErrors).some(Boolean);
        this.errorMessage = hasField && err.status === 400 ? '' : err.message;
      },
    });
  }
}
