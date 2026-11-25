import { DatePipe } from '@angular/common';
import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { CrmActivity } from '../../models/activity';
import { CrmApiError, CrmFieldErrors } from '../../models/board';
import { CrmRelated } from '../../models/task';
import { CrmActivitiesApiService } from '../../services/crm-activities-api.service';
import {
  ActivityFieldsComponent, activityFormValid, activityFormValue, createActivityForm,
} from '../activity-fields/activity-fields.component';

/**
 * «Registrar actividad» de un cliente u oportunidad, con su historial debajo (más reciente primero). Se cierra con la
 * actividad guardada; es autónomo para poder embeberse luego en la ficha 360° del cliente.
 */
@Component({
  selector: 'app-crm-activity-dialog',
  templateUrl: './activity-dialog.component.html',
  imports: [TranslatePipe, ActivityFieldsComponent, DatePipe],
})
export class ActivityDialogComponent {
  readonly form = createActivityForm();
  related!: CrmRelated;
  history: CrmActivity[] = [];
  historyTotal = 0;
  historyLoading = false;
  historyError = '';
  historyPage = 1;
  saving = false;
  errorMessage = '';
  conflict = false;
  fieldErrors: CrmFieldErrors = {};

  readonly activeModal = inject(NgbActiveModal);
  private api = inject(CrmActivitiesApiService);
  private destroyRef = inject(DestroyRef);

  constructor() {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.fieldErrors = {};
      this.errorMessage = '';
    });
  }

  open(related: CrmRelated): void {
    this.related = related;
    this.loadHistory();
  }

  get canSave(): boolean {
    return !this.saving && activityFormValid(this.form);
  }

  get hasMoreHistory(): boolean {
    return this.history.length < this.historyTotal;
  }

  /** Carga la primera página del historial, o la siguiente (se agrega al final) con `more`. */
  loadHistory(more = false): void {
    this.historyLoading = true;
    this.historyError = '';
    const page = more ? this.historyPage + 1 : 1;
    this.api.list(this.related, page).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (result) => {
        this.historyLoading = false;
        this.historyPage = page;
        this.history = more ? [...this.history, ...result.results] : result.results;
        this.historyTotal = result.count;
      },
      error: (err: CrmApiError) => {
        this.historyLoading = false;
        this.historyError = err.message;
      },
    });
  }

  save(): void {
    if (!this.canSave) return;
    this.saving = true;
    this.errorMessage = '';
    this.api.create({ related: this.related, ...activityFormValue(this.form) }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (saved) => {
        this.saving = false;
        this.activeModal.close(saved);
      },
      error: (err: CrmApiError) => {
        this.saving = false;
        this.fieldErrors = err.fieldErrors;
        this.conflict = err.status === 409;
        this.errorMessage = Object.keys(err.fieldErrors).length ? '' : err.message;
      },
    });
  }
}
