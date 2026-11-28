import { Component, DestroyRef, ElementRef, OnInit, ViewChild, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { TranslatePipe } from '@ngx-translate/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { tr } from '../../../core/i18n/translate';
import { statusLabel } from '../../agenda/models/appointment';
import { formatDateTime } from '../../agenda/services/appointments-api.service';
import {
  CANCEL_REASON_MAX, EncounterAction, EncounterDetail, EncounterStatus, OBSERVATIONS_MAX,
  appointmentTone, encounterStatusLabel, encounterTone,
} from '../models/encounter';
import { EncountersApiService, encounterFailure } from '../services/encounters-api.service';

/** Atención odontológica de una cita: resumen del paciente, estado clínico, odontograma opcional y observaciones. */
@Component({
  selector: 'app-encounter-detail',
  imports: [ReactiveFormsModule, RouterLink, TranslatePipe],
  templateUrl: './encounter-detail.component.html',
  styleUrl: './encounter-detail.component.scss',
})
export class EncounterDetailComponent implements OnInit {
  private api = inject(EncountersApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
  private fb = inject(FormBuilder).nonNullable;

  @ViewChild('cancelDialog') cancelDialog?: ElementRef<HTMLDialogElement>;
  @ViewChild('finishDialog') finishDialog?: ElementRef<HTMLDialogElement>;

  readonly statusLabel = statusLabel;
  readonly encounterLabel = encounterStatusLabel;
  readonly formatDateTime = formatDateTime;
  readonly reasonMax = CANCEL_REASON_MAX;
  readonly observationsMax = OBSERVATIONS_MAX;
  readonly reason = this.fb.control('', [Validators.required, Validators.maxLength(CANCEL_REASON_MAX)]);
  readonly observations = this.fb.control('', [Validators.maxLength(OBSERVATIONS_MAX)]);

  detail?: EncounterDetail;
  loading = true;
  saving = false;
  error = '';
  dialogError = '';
  success = '';

  ngOnInit(): void {
    this.load();
  }

  get appointmentId(): string {
    return this.route.snapshot.paramMap.get('appointmentId') ?? '';
  }

  get encounterStatus(): EncounterStatus {
    return this.detail?.encounter?.status ?? 'pending';
  }

  can(action: EncounterAction): boolean {
    return !!this.detail?.allowed_actions.includes(action);
  }

  get inProgress(): boolean {
    return this.encounterStatus === 'in_progress';
  }

  get age(): number | null {
    const birth = this.detail?.patient.birth_date;
    if (!birth) return null;
    const born = new Date(`${birth}T00:00:00`);
    const now = new Date();
    let years = now.getFullYear() - born.getFullYear();
    if (now.getMonth() < born.getMonth() || (now.getMonth() === born.getMonth() && now.getDate() < born.getDate())) years--;
    return years >= 0 ? years : null;
  }

  readonly appointmentTone = appointmentTone;
  readonly encounterTone = encounterTone;

  /** Lo que el odontólogo debe ver antes de tocar al paciente: alergias, antecedentes médicos y medicación. */
  get clinicalAlerts(): string[] {
    const patient = this.detail?.patient;
    if (!patient) return [];
    const lines: [string, string | undefined][] = [
      [tr('DENTISTRY.ENCOUNTER.ALERGIAS'), patient.allergies], [tr('DENTISTRY.ENCOUNTER.ANTECEDENTES_MEDICOS'), patient.medical_history],
      [tr('DENTISTRY.ENCOUNTER.MEDICACION'), patient.medication],
    ];
    return lines.filter(([, value]) => !!value?.trim()).map(([label, value]) => `${label}: ${value?.trim()}`);
  }

  get observationsDirty(): boolean {
    return this.observations.value !== (this.detail?.encounter?.observations ?? '');
  }

  get canSubmitCancel(): boolean {
    return !this.saving && this.reason.valid && !!this.reason.value.trim();
  }

  get startHint(): string {
    if (!this.detail || this.detail.encounter || this.can('start')) return '';
    const key = !this.detail.is_dental ? 'AVISO_NO_ODONTOLOGICA' : ['cancelled', 'no_show', 'attended'].includes(this.detail.appointment.status)
      ? 'AVISO_CITA_CERRADA' : 'AVISO_HORA';
    return tr(`DENTISTRY.ENCOUNTER.${key}`);
  }

  load(): void {
    this.loading = true;
    this.error = '';
    this.api.detail(this.appointmentId).pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.loading = false))
      .subscribe({ next: detail => this.apply(detail), error: failure => this.error = encounterFailure(failure).message });
  }

  private apply(detail: EncounterDetail): void {
    this.detail = detail;
    this.observations.setValue(detail.encounter?.observations ?? '', { emitEvent: false });
    if (detail.encounter && detail.encounter.status === 'in_progress') this.observations.enable({ emitEvent: false });
    else this.observations.disable({ emitEvent: false });
  }

  run(action: 'start' | 'finish'): void {
    if (this.saving) return;
    this.saving = true;
    this.error = '';
    this.success = '';
    this.api.act(this.appointmentId, action).pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.saving = false))
      .subscribe({
        next: detail => { this.apply(detail); this.success = tr(`DENTISTRY.ENCOUNTER.OK_${action.toUpperCase()}`); },
        error: failure => { this.error = encounterFailure(failure).message; this.refresh(); },
      });
  }

  openFinish(): void {
    if (this.saving) return;
    this.finishDialog?.nativeElement.showModal();
  }

  closeFinish(): void {
    this.finishDialog?.nativeElement.close();
  }

  /** Finaliza sin perder lo escrito: las observaciones pendientes se guardan antes de cerrar la atención. */
  confirmFinish(): void {
    const encounter = this.detail?.encounter;
    if (!encounter || this.saving) return;
    this.closeFinish();
    if (this.observations.value === encounter.observations) {
      this.run('finish');
      return;
    }
    this.saving = true;
    this.error = '';
    this.api.saveObservations(encounter.id, this.observations.value).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: detail => { this.saving = false; this.apply(detail); this.run('finish'); },
      error: failure => { this.saving = false; this.error = encounterFailure(failure).message; },
    });
  }

  openCancel(): void {
    this.reason.reset('');
    this.dialogError = '';
    this.cancelDialog?.nativeElement.showModal();
  }

  closeCancel(): void {
    if (this.saving) return;
    this.cancelDialog?.nativeElement.close();
  }

  confirmCancel(): void {
    if (!this.canSubmitCancel) return;
    this.saving = true;
    this.dialogError = '';
    this.api.act(this.appointmentId, 'cancel', this.reason.value.trim())
      .pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.saving = false))
      .subscribe({
        next: detail => {
          this.apply(detail);
          this.success = tr('DENTISTRY.ENCOUNTER.OK_CANCEL');
          this.cancelDialog?.nativeElement.close();
        },
        error: failure => { this.dialogError = encounterFailure(failure).message; this.refresh(); },
      });
  }

  saveObservations(): void {
    const encounter = this.detail?.encounter;
    if (!encounter || this.saving || this.observations.invalid) return;
    this.saving = true;
    this.error = '';
    this.api.saveObservations(encounter.id, this.observations.value)
      .pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.saving = false))
      .subscribe({
        next: detail => { this.apply(detail); this.success = tr('DENTISTRY.ENCOUNTER.OK_OBSERVACIONES'); },
        error: failure => this.error = encounterFailure(failure).message,
      });
  }

  addOdontogram(): void {
    const encounter = this.detail?.encounter;
    if (!encounter || this.saving) return;
    this.saving = true;
    this.error = '';
    this.api.createOdontogram(encounter.id).pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.saving = false))
      .subscribe({
        next: evaluation => this.openOdontogram(evaluation.id),
        error: failure => { this.error = encounterFailure(failure).message; this.refresh(); },
      });
  }

  openOdontogram(evaluationId: string): void {
    if (!this.detail) return;
    void this.router.navigate(['/pocketbiz/dentistry/patients', this.detail.appointment.customer_id, 'odontogram'], {
      queryParams: { evaluation: evaluationId, appointment: this.appointmentId },
    });
  }

  /** Tras un conflicto se relee el estado vigente sin perder el mensaje mostrado. */
  private refresh(): void {
    this.api.detail(this.appointmentId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({ next: detail => this.apply(detail) });
  }
}
