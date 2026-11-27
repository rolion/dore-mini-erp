import { DatePipe, NgClass } from '@angular/common';
import { Component, DestroyRef, Input, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { TranslatePipe } from '@ngx-translate/core';
import { CrmActivity, CrmActivityOutcome } from '../../models/activity';
import { CrmApiError, CrmFieldErrors } from '../../models/board';
import { CrmRelated } from '../../models/task';
import { CrmActivitiesApiService } from '../../services/crm-activities-api.service';
import {
  ActivityFieldsComponent, activityFormValid, activityFormValue, createActivityForm,
} from '../activity-fields/activity-fields.component';

/**
 * Actividades de una oportunidad embebidas en una pantalla (p. ej. la ficha de la tarjeta): «Agregar actividad» abre el
 * formulario arriba y el historial va debajo, más reciente primero.
 */
@Component({
  selector: 'app-crm-activity-panel',
  templateUrl: './activity-panel.component.html',
  imports: [TranslatePipe, ActivityFieldsComponent, DatePipe, NgClass],
  // El panel llena la altura fija de la ficha: el formulario queda arriba (con su propio scroll) y el historial ocupa el
  // resto con scroll, así abrir el formulario no agranda el modal.
  styles: [':host { display: block; height: 100%; } .activity-panel { display: flex; flex-direction: column; height: 100%; } .activity-history { flex: 1 1 0; min-height: 6rem; overflow-y: auto; }'],
})
export class ActivityPanelComponent implements OnInit {
  @Input({ required: true }) related!: CrmRelated;

  readonly form = createActivityForm();
  formOpen = false;
  history: CrmActivity[] = [];
  historyTotal = 0;
  historyPage = 1;
  historyLoading = false;
  historyError = '';
  saving = false;
  errorMessage = '';
  fieldErrors: CrmFieldErrors = {};

  private api = inject(CrmActivitiesApiService);
  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.fieldErrors = {};
      this.errorMessage = '';
    });
    this.loadHistory();
  }

  get canSave(): boolean {
    return !this.saving && activityFormValid(this.form);
  }

  get hasMoreHistory(): boolean {
    return this.history.length < this.historyTotal;
  }

  toggleForm(): void {
    this.formOpen = !this.formOpen;
  }

  outcomeClass(outcome: CrmActivityOutcome): string {
    switch (outcome) {
      case 'contacted':
      case 'interested':
        return 'col-green';
      case 'no_answer':
        return 'col-orange';
      case 'not_interested':
        return 'col-red';
      default:
        return 'col-cyan';
    }
  }

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
      next: () => {
        this.saving = false;
        this.form.reset({ channel: 'call', outcome: '', notes: '', occurredAt: '' });
        this.formOpen = false;
        this.loadHistory();
      },
      error: (err: CrmApiError) => {
        this.saving = false;
        this.fieldErrors = err.fieldErrors;
        this.errorMessage = Object.keys(err.fieldErrors).length ? '' : err.message;
      },
    });
  }
}
