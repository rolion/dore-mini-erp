import { HttpErrorResponse } from '@angular/common/http';
import { DatePipe, NgTemplateOutlet } from '@angular/common';
import { Component, DestroyRef, HostListener, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { CLINICAL_FIELDS, ClinicalInput, Patient } from '../models/patient';
import { DentistryApiService, errorMessage, fieldErrors } from '../services/dentistry-api.service';
import { demographicsValidator, localDateInput, minorAt } from '../services/demographics-form';
import { PatientHistoryComponent } from '../components/patient-history.component';

@Component({
  selector: 'app-patient-detail', imports: [DatePipe, NgTemplateOutlet, RouterLink, ReactiveFormsModule, PatientHistoryComponent],
  templateUrl: './patient-detail.component.html',
  styles: [`
    :host-context(.dark) h3 {
      color: var(--bs-gray-400) !important;
    }
    :host-context(body:not(.dark)) .btn-outline-warning:not(:hover) {
      color: var(--bs-warning-text-emphasis);
    }
    .fst-italic.text-muted {
      color: inherit !important;
      opacity: .8;
    }
  `],
})
export class PatientDetailComponent implements OnInit {
  private api = inject(DentistryApiService);
  private route = inject(ActivatedRoute);
  private fb = inject(FormBuilder).nonNullable;
  private destroyRef = inject(DestroyRef);
  readonly id = this.route.snapshot.paramMap.get('id') ?? '';
  readonly fields = CLINICAL_FIELDS;
  readonly today = localDateInput();
  readonly backFilters = { search: this.route.snapshot.queryParamMap.get('search') ?? '',
    active: this.route.snapshot.queryParamMap.get('active') ?? 'true', page: this.route.snapshot.queryParamMap.get('page') ?? '1' };
  patient: Patient | null = null;
  loading = false;
  savingClinical = false;
  savingAdmin = false;
  savingState = false;
  editingAdmin = false;
  editingClinical = false;
  historyOpen = false;
  error = '';
  success = '';
  clinicalErrors: Record<string, string> = {};
  adminErrors: Record<string, string> = {};
  clinicalRevision = 0;
  adminRevision = 0;
  clinicalForm = this.fb.group({
    medical_history: ['', Validators.maxLength(4000)], dental_history: ['', Validators.maxLength(4000)],
    allergies: ['', Validators.maxLength(4000)], medication: ['', Validators.maxLength(4000)], clinical_notes: ['', Validators.maxLength(4000)],
  });
  adminForm = this.fb.group({ birth_date: '', responsible_name: ['', Validators.maxLength(150)],
    responsible_phone: ['', Validators.maxLength(30)] }, { validators: demographicsValidator });
  get saving() { return this.savingClinical || this.savingAdmin || this.savingState; }
  get needsResponsible() { return minorAt(this.adminForm.controls.birth_date.value); }
  ngOnInit() {
    this.adminForm.controls.birth_date.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(birth => {
      if (!minorAt(birth) && this.patient) {
        this.adminForm.patchValue({
          responsible_name: this.patient.customer.responsible_name,
          responsible_phone: this.patient.customer.responsible_phone,
        }, { emitEvent: false, onlySelf: true });
      }
    });
    this.load();
  }
  editRecord() {
    if (this.patient?.active && !this.saving) {
      this.editingAdmin = true;
      this.editingClinical = true;
    }
  }
  load() {
    this.loading = true; this.error = '';
    this.api.get(this.id).pipe(finalize(() => this.loading = false), takeUntilDestroyed(this.destroyRef)).subscribe({
      next: patient => {
        this.patient = patient;
        this.clinicalForm.reset(this.clinicalValues(patient));
        this.adminForm.reset({ birth_date: patient.customer.birth_date ?? '', responsible_name: patient.customer.responsible_name,
          responsible_phone: patient.customer.responsible_phone });
        this.setFormState(patient.active);
        if (this.route.snapshot.queryParamMap.get('created') === 'true') this.success = 'Perfil odontológico creado.';
      }, error: (error: HttpErrorResponse) => this.error = errorMessage(error),
    });
  }
  saveClinical() {
    if (!this.patient?.active || this.saving || !this.clinicalForm.dirty) return;
    this.clinicalForm.markAllAsTouched();
    if (this.clinicalForm.invalid) return;
    this.savingClinical = true; this.error = ''; this.success = ''; this.clinicalErrors = {};
    this.api.update(this.id, this.clinicalForm.getRawValue()).pipe(
      finalize(() => this.savingClinical = false), takeUntilDestroyed(this.destroyRef),
    ).subscribe({ next: patient => {
      // Preserve an independently edited administrative form.
      this.patient = patient; this.clinicalForm.reset(this.clinicalValues(patient)); this.clinicalRevision++;
      this.editingClinical = false;
      this.success = 'Antecedentes guardados.';
    }, error: (error: HttpErrorResponse) => { this.error = errorMessage(error); this.clinicalErrors = fieldErrors(error); } });
  }
  saveAdmin() {
    if (!this.patient?.active || this.saving || !this.adminForm.dirty) return;
    this.adminForm.markAllAsTouched();
    if (this.adminForm.invalid) return;
    this.savingAdmin = true; this.error = ''; this.success = ''; this.adminErrors = {};
    const input = this.adminForm.getRawValue();
    this.api.demographics(this.id, { ...input, birth_date: input.birth_date || null }).pipe(
      finalize(() => this.savingAdmin = false), takeUntilDestroyed(this.destroyRef),
    ).subscribe({ next: data => {
      if (this.patient) this.patient = { ...this.patient, customer: { ...this.patient.customer, ...data } };
      this.adminForm.reset({ ...data, birth_date: data.birth_date ?? '' }); this.adminRevision++;
      this.editingAdmin = false;
      this.success = 'Datos administrativos guardados.';
    }, error: (error: HttpErrorResponse) => { this.error = errorMessage(error); this.adminErrors = fieldErrors(error); } });
  }
  toggleActive() {
    if (!this.patient || this.saving) return;
    if (this.hasUnsavedChanges()) { this.error = 'Guarda o cancela los cambios antes de cambiar el estado.'; return; }
    const active = !this.patient.active;
    if (!window.confirm(active ? '¿Reactivar el perfil conservando su historia?' : '¿Archivar el perfil? Se conservará su historia y el cliente seguirá disponible.')) return;
    this.savingState = true; this.error = ''; this.success = '';
    this.api.setActive(this.id, active).pipe(finalize(() => this.savingState = false), takeUntilDestroyed(this.destroyRef)).subscribe({
      next: patient => { this.patient = patient; this.setFormState(patient.active); this.clinicalRevision++;
        this.success = active ? 'Perfil reactivado.' : 'Perfil archivado. Se conserva su historia.'; },
      error: (error: HttpErrorResponse) => this.error = errorMessage(error),
    });
  }
  cancelClinical() { this.editingClinical = false; if (this.patient) { this.clinicalForm.reset(this.clinicalValues(this.patient)); this.clinicalErrors = {}; } }
  cancelAdmin() {
    this.editingAdmin = false;
    if (this.patient) { this.adminForm.reset({ birth_date: this.patient.customer.birth_date ?? '',
      responsible_name: this.patient.customer.responsible_name, responsible_phone: this.patient.customer.responsible_phone }); this.adminErrors = {}; }
  }
  hasUnsavedChanges() { return this.saving || this.clinicalForm.dirty || this.adminForm.dirty; }
  @HostListener('window:beforeunload', ['$event'])
  beforeUnload(event: BeforeUnloadEvent) { if (this.hasUnsavedChanges()) { event.preventDefault(); event.returnValue = ''; } }
  private setFormState(active: boolean) {
    this.editingAdmin = false;
    this.editingClinical = false;
    if (active) { this.clinicalForm.enable(); this.adminForm.enable(); }
    else { this.clinicalForm.disable(); this.adminForm.disable(); }
  }
  private clinicalValues(patient: Patient): ClinicalInput {
    return { medical_history: patient.medical_history, dental_history: patient.dental_history,
      allergies: patient.allergies, medication: patient.medication, clinical_notes: patient.clinical_notes };
  }
}
