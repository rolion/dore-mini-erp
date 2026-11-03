import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import {
  Appointment, AppointmentAction, AppointmentFailure, EVENT_LABELS, REASON_MAX_LENGTH, STATUS_CLASSES, STATUS_LABELS,
} from '../models/appointment';
import {
  AppointmentsApiService, formatDateTime, toLocalInput, toServerDateTime,
} from '../services/appointments-api.service';

const ACTION_TITLES: Record<AppointmentAction, string> = {
  confirm: 'Confirmar cita',
  reschedule: 'Reprogramar cita',
  cancel: 'Cancelar cita',
  attend: 'Marcar como atendida',
  no_show: 'Marcar como no asistió',
};

const ACTION_BUTTONS: Record<AppointmentAction, string> = {
  confirm: 'Confirmar',
  reschedule: 'Reprogramar',
  cancel: 'Cancelar cita',
  attend: 'Atendida',
  no_show: 'No asistió',
};

const SUCCESS: Record<AppointmentAction, string> = {
  confirm: 'Cita confirmada.',
  reschedule: 'Cita reprogramada.',
  cancel: 'Cita cancelada.',
  attend: 'Cita marcada como atendida. No se registró tratamiento ni pago.',
  no_show: 'Cita marcada como no asistió.',
};

/** Detalle con historial y acciones de ciclo de vida; las acciones salen de `allowed_actions` del servidor. */
@Component({
  selector: 'app-appointment-detail',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './appointment-detail.component.html',
  styleUrl: './appointment-detail.component.scss',
})
export class AppointmentDetailComponent implements OnInit {
  private api = inject(AppointmentsApiService);
  private route = inject(ActivatedRoute);
  private destroyRef = inject(DestroyRef);
  private fb = inject(FormBuilder).nonNullable;

  readonly labels = STATUS_LABELS;
  readonly classes = STATUS_CLASSES;
  readonly events = EVENT_LABELS;
  readonly titles = ACTION_TITLES;
  readonly buttons = ACTION_BUTTONS;
  readonly reasonMax = REASON_MAX_LENGTH;
  readonly formatDateTime = formatDateTime;
  readonly form = this.fb.group({ starts: '', duration_minutes: 30, reason: '' });

  appointment?: Appointment;
  action: AppointmentAction | null = null;
  loading = true;
  saving = false;
  error = '';
  dialogError = '';
  fields: Record<string, string> = {};
  success = '';

  ngOnInit(): void {
    this.load();
  }

  private get id(): string {
    return this.route.snapshot.paramMap.get('id') ?? '';
  }

  load(): void {
    this.loading = true;
    this.error = '';
    this.api.get(this.id).pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.loading = false))
      .subscribe({
        next: appointment => this.appointment = appointment,
        error: () => this.error = 'No se pudo cargar la cita.',
      });
  }

  can(action: AppointmentAction): boolean {
    return !!this.appointment?.allowed_actions.includes(action);
  }

  get isTerminal(): boolean {
    return !!this.appointment && !['scheduled', 'confirmed'].includes(this.appointment.status);
  }

  get reason(): string {
    return this.form.controls.reason.value.trim();
  }

  get canSubmit(): boolean {
    if (this.saving || !this.action) return false;
    if (this.action === 'cancel' || this.action === 'reschedule') {
      if (!this.reason || this.reason.length > this.reasonMax) return false;
    }
    return this.action !== 'reschedule' || (!!this.form.controls.starts.value && this.form.controls.duration_minutes.value >= 1);
  }

  open(dialog: HTMLDialogElement, action: AppointmentAction): void {
    if (!this.appointment) return;
    this.action = action;
    this.dialogError = '';
    this.fields = {};
    this.form.reset({
      starts: toLocalInput(this.appointment.starts), duration_minutes: this.appointment.duration_minutes, reason: '',
    });
    dialog.showModal();
  }

  close(dialog: HTMLDialogElement): void {
    if (this.saving) return;
    dialog.close();
    this.action = null;
  }

  submit(dialog: HTMLDialogElement): void {
    const action = this.action;
    if (!action || !this.canSubmit) return;
    const value = this.form.getRawValue();
    const body: Record<string, unknown> = {};
    if (action === 'cancel') body['reason'] = value.reason;
    if (action === 'reschedule') {
      Object.assign(body, {
        starts: toServerDateTime(value.starts), duration_minutes: value.duration_minutes, reason: value.reason,
      });
    }
    this.saving = true;
    this.dialogError = '';
    this.api.act(this.id, action, body).pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.saving = false))
      .subscribe({
        next: appointment => {
          this.appointment = appointment;
          this.success = SUCCESS[action];
          dialog.close();
          this.action = null;
        },
        error: (failure: AppointmentFailure) => {
          this.dialogError = failure.message;
          this.fields = failure.fields;
          if (failure.conflict) this.refresh();
        },
      });
  }

  /** Ante un conflicto se relee la cita para mostrar el estado actual sin perder lo escrito en el diálogo. */
  private refresh(): void {
    this.api.get(this.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: appointment => this.appointment = appointment,
    });
  }

  get newEnds(): string {
    const { starts, duration_minutes } = this.form.getRawValue();
    if (!starts || duration_minutes < 1) return '—';
    const date = new Date(`${starts}:00Z`);
    date.setUTCMinutes(date.getUTCMinutes() + duration_minutes);
    const iso = date.toISOString();
    return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)} ${iso.slice(11, 16)}`;
  }

  get newStarts(): string {
    const { starts } = this.form.getRawValue();
    return starts ? formatDateTime(starts) : '—';
  }
}
