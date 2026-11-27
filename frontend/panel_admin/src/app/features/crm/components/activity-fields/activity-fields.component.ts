import { Component, Input } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { TranslatePipe } from '@ngx-translate/core';
import {
  CRM_ACTIVITY_CHANNELS, CRM_ACTIVITY_NOTES_MAX_LENGTH, CRM_ACTIVITY_OUTCOMES, CrmActivityChannel, CrmActivityDetails,
  CrmActivityOutcome,
} from '../../models/activity';
import { CrmFieldErrors } from '../../models/board';
import { fromLocalInput } from '../opportunity-dialog/opportunity-dialog.component';

export interface ActivityFormControls {
  channel: FormControl<CrmActivityChannel>;
  outcome: FormControl<CrmActivityOutcome | ''>;
  notes: FormControl<string>;
  occurredAt: FormControl<string>;
}

/** Formulario de actividad compartido por «Registrar actividad» y «Completar tarea». */
export function createActivityForm(): FormGroup<ActivityFormControls> {
  return new FormGroup<ActivityFormControls>({
    channel: new FormControl<CrmActivityChannel>('call', { nonNullable: true, validators: Validators.required }),
    outcome: new FormControl<CrmActivityOutcome | ''>('', { nonNullable: true }),
    notes: new FormControl('', { nonNullable: true, validators: Validators.maxLength(CRM_ACTIVITY_NOTES_MAX_LENGTH) }),
    occurredAt: new FormControl('', { nonNullable: true }),
  });
}

/** Con resultado o notas la actividad es válida (el servidor aplica la misma regla). */
export function activityFormValid(form: FormGroup<ActivityFormControls>): boolean {
  const { outcome, notes } = form.getRawValue();
  return form.valid && (!!outcome || !!notes.trim());
}

export function activityFormValue(form: FormGroup<ActivityFormControls>): CrmActivityDetails {
  const value = form.getRawValue();
  const occurredAt = fromLocalInput(value.occurredAt);
  return { channel: value.channel, outcome: value.outcome, notes: value.notes, ...(occurredAt ? { occurredAt } : {}) };
}

/** Campos canal, resultado, notas y (opcional) fecha y hora de una actividad. */
@Component({
  selector: 'app-crm-activity-fields',
  templateUrl: './activity-fields.component.html',
  imports: [TranslatePipe, ReactiveFormsModule],
})
export class ActivityFieldsComponent {
  @Input({ required: true }) form!: FormGroup<ActivityFormControls>;
  @Input() showDate = false;
  /** Fecha antes de la nota (formulario embebido de la tarjeta). */
  @Input() dateFirst = false;
  /** Errores del servidor por campo (`channel`, `outcome`, `notes`, `occurredAt`). */
  @Input() errors: CrmFieldErrors = {};
  /** Prefijo único de ids cuando hay dos formularios en pantalla. */
  @Input() idPrefix = 'crm-activity';

  readonly channels = CRM_ACTIVITY_CHANNELS;
  readonly outcomes = CRM_ACTIVITY_OUTCOMES;
  readonly notesMaxLength = CRM_ACTIVITY_NOTES_MAX_LENGTH;

  get notesLength(): number {
    return this.form.controls.notes.value.length;
  }
}
