import { tr } from '../../../core/i18n/translate';
import { TranslatePipe } from '@ngx-translate/core';
import { HttpErrorResponse } from '@angular/common/http';
import { DatePipe, NgTemplateOutlet } from '@angular/common';
import { Component, DestroyRef, ElementRef, HostListener, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import Swal from 'sweetalert2';
import { CLINICAL_FIELDS, ClinicalField, ClinicalInput, Patient } from '../models/patient';
import { DentistryApiService, errorMessage, fieldErrors } from '../services/dentistry-api.service';
import { ageAt, demographicsValidator, localDateInput, minorAt } from '../services/demographics-form';
import { PatientHistoryComponent } from '../components/patient-history.component';
import { PatientProformasComponent } from '../components/patient-proformas.component';

export type SectionState = 'idle' | 'saving' | 'saved' | 'error';
export type Section = 'clinical' | 'admin';
const CLINICAL_LIMIT = 4000;
const COUNTER_FROM = 3200;

@Component({
  selector: 'app-patient-detail', imports: [TranslatePipe, DatePipe, NgTemplateOutlet, RouterLink, ReactiveFormsModule, PatientHistoryComponent, PatientProformasComponent],
  templateUrl: './patient-detail.component.html',
  styles: [`
    :host-context(.dark) h3 {
      color: var(--bs-gray-400) !important;
    }
    textarea { overflow: hidden; resize: none; }
  `],
})
export class PatientDetailComponent implements OnInit {
  private api = inject(DentistryApiService);
  private route = inject(ActivatedRoute);
  private fb = inject(FormBuilder).nonNullable;
  private destroyRef = inject(DestroyRef);
  private host = inject<ElementRef<HTMLElement>>(ElementRef);
  readonly id = this.route.snapshot.paramMap.get('id') ?? '';
  readonly fields = CLINICAL_FIELDS;
  readonly summaryFields = CLINICAL_FIELDS.filter(field => field.key === 'allergies' || field.key === 'medication');
  readonly backgroundFields = CLINICAL_FIELDS.filter(field => field.key !== 'allergies' && field.key !== 'medication');
  readonly today = localDateInput();
  readonly limit = CLINICAL_LIMIT;
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
  historyTab: Section = 'clinical';
  error = '';
  success = '';
  clinicalState: SectionState = 'idle';
  adminState: SectionState = 'idle';
  clinicalMessage = '';
  adminMessage = '';
  clinicalErrors: Record<string, string> = {};
  adminErrors: Record<string, string> = {};
  clinicalRevision = 0;
  adminRevision = 0;
  clinicalForm = this.fb.group({
    medical_history: ['', Validators.maxLength(CLINICAL_LIMIT)], dental_history: ['', Validators.maxLength(CLINICAL_LIMIT)],
    allergies: ['', Validators.maxLength(CLINICAL_LIMIT)], medication: ['', Validators.maxLength(CLINICAL_LIMIT)], clinical_notes: ['', Validators.maxLength(CLINICAL_LIMIT)],
  });
  adminForm = this.fb.group({ birth_date: '', responsible_name: ['', Validators.maxLength(150)],
    responsible_phone: ['', Validators.maxLength(30)] }, { validators: demographicsValidator });
  get saving() { return this.savingClinical || this.savingAdmin || this.savingState; }
  get needsResponsible() { return minorAt(this.adminForm.controls.birth_date.value); }
  /** Edad y condición de menor según lo guardado (no según el borrador del formulario). */
  get age(): number | null { return ageAt(this.patient?.customer.birth_date); }
  get isMinor(): boolean { return this.age !== null && this.age < 18; }
  get ageText(): string { return tr(this.age === 1 ? 'DENTISTRY.PATIENT_DETAIL.EDAD_ANO' : 'DENTISTRY.PATIENT_DETAIL.EDAD_ANOS', { n: this.age }); }
  get minorText(): string { return tr(this.age === 1 ? 'DENTISTRY.PATIENT_DETAIL.MENOR_EDAD_ANO' : 'DENTISTRY.PATIENT_DETAIL.MENOR_EDAD_ANOS', { n: this.age }); }
  get missingResponsible(): boolean {
    return this.isMinor && !(this.patient?.customer.responsible_name.trim() && this.patient?.customer.responsible_phone.trim());
  }
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
  editClinical(focus?: ClinicalField) {
    if (!this.patient?.active || this.saving) return;
    this.editingClinical = true; this.clinicalState = 'idle'; this.clinicalMessage = '';
    this.focusLater(`#${focus ?? 'medical_history'}`, true);
  }
  editAdmin() {
    if (!this.patient?.active || this.saving) return;
    this.editingAdmin = true; this.adminState = 'idle'; this.adminMessage = '';
    this.focusLater('#birth-date');
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
        if (this.route.snapshot.queryParamMap.get('created') === 'true') {
          this.success = tr('DENTISTRY.PATIENT_DETAIL.PERFIL_ODONTOLOGICO_CREADO');
          this.focusLater('#clinical-section');
        }
      }, error: (error: HttpErrorResponse) => this.error = errorMessage(error),
    });
  }
  saveClinical() {
    if (!this.patient?.active || this.saving || !this.clinicalForm.dirty) return;
    this.clinicalForm.markAllAsTouched();
    if (this.clinicalForm.invalid) return;
    this.error = ''; this.savingClinical = true; this.clinicalState = 'saving'; this.clinicalMessage = ''; this.clinicalErrors = {};
    this.api.update(this.id, this.clinicalForm.getRawValue()).pipe(
      finalize(() => this.savingClinical = false), takeUntilDestroyed(this.destroyRef),
    ).subscribe({ next: patient => {
      // Preserve an independently edited administrative form.
      this.patient = patient; this.clinicalForm.reset(this.clinicalValues(patient)); this.clinicalRevision++;
      this.editingClinical = false; this.clinicalState = 'saved';
      this.focusLater('#clinical-edit-btn');
    }, error: (error: HttpErrorResponse) => {
      this.clinicalState = 'error'; this.clinicalMessage = errorMessage(error); this.clinicalErrors = fieldErrors(error);
      this.focusLater('#clinical-section [aria-invalid="true"]');
    } });
  }
  saveAdmin() {
    if (!this.patient?.active || this.saving || !this.adminForm.dirty) return;
    this.adminForm.markAllAsTouched();
    if (this.adminForm.invalid) return;
    this.error = ''; this.savingAdmin = true; this.adminState = 'saving'; this.adminMessage = ''; this.adminErrors = {};
    const input = this.adminForm.getRawValue();
    this.api.demographics(this.id, { ...input, birth_date: input.birth_date || null }).pipe(
      finalize(() => this.savingAdmin = false), takeUntilDestroyed(this.destroyRef),
    ).subscribe({ next: data => {
      if (this.patient) this.patient = { ...this.patient, customer: { ...this.patient.customer, ...data } };
      this.adminForm.reset({ ...data, birth_date: data.birth_date ?? '' }); this.adminRevision++;
      this.editingAdmin = false; this.adminState = 'saved';
      this.focusLater('#admin-edit-btn');
    }, error: (error: HttpErrorResponse) => {
      this.adminState = 'error'; this.adminMessage = errorMessage(error); this.adminErrors = fieldErrors(error);
      this.focusLater('#admin-section [aria-invalid="true"]');
    } });
  }
  async toggleActive() {
    if (!this.patient || this.saving) return;
    const pending = this.pendingSections();
    if (pending.length) { this.error = tr('DENTISTRY.PATIENT_DETAIL.GUARDA_O_CANCELA_LOS_CAMBIOS', { sections: pending.join(', ') }); return; }
    const active = !this.patient.active;
    if (!await this.confirmStateChange(active)) return;
    this.savingState = true; this.error = ''; this.success = '';
    this.api.setActive(this.id, active).pipe(finalize(() => this.savingState = false), takeUntilDestroyed(this.destroyRef)).subscribe({
      next: patient => { this.patient = patient; this.setFormState(patient.active); this.clinicalRevision++;
        this.clinicalState = 'idle'; this.adminState = 'idle';
        this.success = active ? tr('DENTISTRY.PATIENT_DETAIL.PERFIL_REACTIVADO') : tr('DENTISTRY.PATIENT_DETAIL.PERFIL_ARCHIVADO_SE_CONSERVA_SU'); },
      error: (error: HttpErrorResponse) => this.error = errorMessage(error),
    });
  }
  /** Diálogo de confirmación (separado para poder sustituirlo en pruebas). */
  async confirmStateChange(activate: boolean): Promise<boolean> {
    const name = this.patient?.customer.name ?? '';
    const result = await Swal.fire({
      title: tr(activate ? 'DENTISTRY.PATIENT_DETAIL.DIALOG_REACTIVAR_TITULO' : 'DENTISTRY.PATIENT_DETAIL.DIALOG_ARCHIVAR_TITULO', { name }),
      text: tr(activate ? 'DENTISTRY.PATIENT_DETAIL.DIALOG_REACTIVAR_TEXTO' : 'DENTISTRY.PATIENT_DETAIL.DIALOG_ARCHIVAR_TEXTO'),
      showCancelButton: true, buttonsStyling: false,
      confirmButtonText: tr(activate ? 'DENTISTRY.PATIENT_DETAIL.REACTIVAR_PERFIL' : 'DENTISTRY.PATIENT_DETAIL.ARCHIVAR_PERFIL'),
      cancelButtonText: tr('COMMON.CANCELAR'),
      customClass: { confirmButton: 'btn btn-warning', cancelButton: 'btn btn-light ms-2' },
    });
    return result.isConfirmed;
  }
  cancelClinical() {
    this.error = ''; this.editingClinical = false; this.clinicalState = 'idle'; this.clinicalMessage = '';
    if (this.patient) { this.clinicalForm.reset(this.clinicalValues(this.patient)); this.clinicalErrors = {}; }
    this.focusLater('#clinical-edit-btn');
  }
  cancelAdmin() {
    this.error = ''; this.editingAdmin = false; this.adminState = 'idle'; this.adminMessage = '';
    if (this.patient) { this.adminForm.reset({ birth_date: this.patient.customer.birth_date ?? '',
      responsible_name: this.patient.customer.responsible_name, responsible_phone: this.patient.customer.responsible_phone }); this.adminErrors = {}; }
    this.focusLater('#admin-edit-btn');
  }
  /** Texto de la línea de estado de una sección (región `aria-live`). */
  statusText(section: Section): string {
    const clinical = section === 'clinical';
    const state = clinical ? this.clinicalState : this.adminState;
    const editing = clinical ? this.editingClinical : this.editingAdmin;
    const dirty = (clinical ? this.clinicalForm : this.adminForm).dirty;
    if (state === 'saving') return tr('DENTISTRY.PATIENT_DETAIL.GUARDANDO');
    if (state === 'error') return `${tr('DENTISTRY.PATIENT_DETAIL.NO_SE_PUDO_GUARDAR')} ${clinical ? this.clinicalMessage : this.adminMessage}`.trim();
    if (editing) return tr(dirty ? 'DENTISTRY.PATIENT_DETAIL.CAMBIOS_SIN_GUARDAR' : 'DENTISTRY.PATIENT_DETAIL.SIN_CAMBIOS');
    return state === 'saved' ? tr('DENTISTRY.PATIENT_DETAIL.GUARDADO') : '';
  }
  length(field: ClinicalField): number { return this.clinicalForm.controls[field].value.length; }
  showCounter(field: ClinicalField): boolean { return this.length(field) >= COUNTER_FROM; }
  autosize(event: Event) {
    const area = event.target as HTMLTextAreaElement;
    area.style.height = 'auto'; area.style.height = `${area.scrollHeight}px`;
  }
  hasUnsavedChanges() { return this.saving || this.clinicalForm.dirty || this.adminForm.dirty; }
  @HostListener('window:beforeunload', ['$event'])
  beforeUnload(event: BeforeUnloadEvent) { if (this.hasUnsavedChanges()) { event.preventDefault(); event.returnValue = ''; } }
  private pendingSections(): string[] {
    const pending: string[] = [];
    if (this.clinicalForm.dirty) pending.push(tr('DENTISTRY.PATIENT_DETAIL.ANTECEDENTES_CLINICOS'));
    if (this.adminForm.dirty) pending.push(tr('DENTISTRY.PATIENT_DETAIL.DATOS_PERSONALES'));
    return pending;
  }
  private focusLater(selector: string, resize = false) {
    setTimeout(() => {
      const element = this.host.nativeElement.querySelector<HTMLElement>(selector);
      element?.focus();
      if (resize) this.host.nativeElement.querySelectorAll<HTMLTextAreaElement>('#clinical-section textarea').forEach(area => {
        area.style.height = 'auto'; area.style.height = `${area.scrollHeight}px`;
      });
    });
  }
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
