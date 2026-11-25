import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { NgSelectModule } from '@ng-select/ng-select';
import { TranslatePipe } from '@ngx-translate/core';
import { Observable, Subject, catchError, debounceTime, distinctUntilChanged, map, of, switchMap, tap } from 'rxjs';
import { CrmApiError } from '../../models/board';
import { CrmContact } from '../../models/lead';
import { CrmOwner } from '../../models/opportunity';
import { CRM_TASK_TITLE_MAX_LENGTH, CrmRelated, CrmTask } from '../../models/task';
import { CrmCustomersApiService } from '../../services/crm-customers-api.service';
import { CrmTasksApiService } from '../../services/crm-tasks-api.service';
import { fromLocalInput, toLocalInput } from '../opportunity-dialog/opportunity-dialog.component';

export interface TaskDialogContext {
  owners: CrmOwner[];
  currentUser: CrmOwner | null;
  /** Relacionado fijo (desde la tarjeta o la fila de un cliente); sin él se elige un cliente. */
  related?: CrmRelated;
  /** Tarea a editar (pendiente); el relacionado no cambia. */
  task?: CrmTask;
}

type TaskField = 'title' | 'dueAt' | 'ownerId' | 'related';

const SEARCH_PAGE_SIZE = 20;

function notBlank(control: AbstractControl<string>): ValidationErrors | null {
  return control.value.trim() ? null : { required: true };
}

/** Alta o edición de una tarea comercial; se cierra devolviendo la tarea guardada. */
@Component({
  selector: 'app-crm-task-dialog',
  templateUrl: './task-dialog.component.html',
  imports: [TranslatePipe, ReactiveFormsModule, NgSelectModule],
})
export class TaskDialogComponent implements OnInit {
  readonly titleMaxLength = CRM_TASK_TITLE_MAX_LENGTH;
  private fb = inject(FormBuilder).nonNullable;
  readonly form = this.fb.group({
    contact: this.fb.control<CrmContact | null>(null),
    title: ['', [notBlank, Validators.maxLength(CRM_TASK_TITLE_MAX_LENGTH)]],
    dueAt: ['', Validators.required],
    ownerId: [''],
  });

  context!: TaskDialogContext;
  contacts: CrmContact[] = [];
  contactsLoading = false;
  readonly contactSearch$ = new Subject<string>();
  saving = false;
  errorMessage = '';
  conflict = false;
  serverErrors: Partial<Record<TaskField, string>> = {};

  readonly activeModal = inject(NgbActiveModal);
  private api = inject(CrmTasksApiService);
  private customersApi = inject(CrmCustomersApiService);
  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.serverErrors = {};
      this.errorMessage = '';
    });
    this.contactSearch$.pipe(
      debounceTime(250),
      distinctUntilChanged(),
      tap(() => (this.contactsLoading = true)),
      switchMap((term) => this.searchCustomers(term.trim())),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe((contacts) => {
      this.contactsLoading = false;
      this.contacts = contacts;
    });
  }

  open(context: TaskDialogContext): void {
    this.context = context;
    const task = context.task;
    if (task) {
      this.form.patchValue({ title: task.title, dueAt: toLocalInput(task.dueAt), ownerId: String(task.owner.id) }, { emitEvent: false });
    } else {
      this.form.controls.ownerId.setValue(context.currentUser ? String(context.currentUser.id) : '', { emitEvent: false });
    }
    if (!task && !context.related) {
      this.form.controls.contact.setValidators(Validators.required);
    }
  }

  get isEdit(): boolean {
    return !!this.context?.task;
  }

  /** La persona debe elegir el cliente solo al crear sin relacionado fijo. */
  get choosesRelated(): boolean {
    return !this.context.task && !this.context.related;
  }

  get relatedName(): string {
    return this.context.task?.related.name ?? this.context.related?.name ?? '';
  }

  get ownerOptions(): CrmOwner[] {
    const all = new Map<number, CrmOwner>();
    for (const owner of [...this.context.owners, ...(this.context.currentUser ? [this.context.currentUser] : []),
      ...(this.context.task ? [this.context.task.owner] : [])]) all.set(owner.id, owner);
    return [...all.values()].sort((a, b) => a.name.localeCompare(b.name));
  }

  invalid(field: TaskField): boolean {
    if (this.serverErrors[field]) return true;
    const control = field === 'related' ? this.form.controls.contact : this.form.controls[field];
    return control.invalid && (control.touched || control.dirty);
  }

  onSubmit(): void {
    this.form.markAllAsTouched();
    if (this.form.invalid || this.saving) return;
    const value = this.form.getRawValue();
    const dueAt = fromLocalInput(value.dueAt);
    if (!dueAt) return;
    const ownerId = value.ownerId ? Number(value.ownerId) : undefined;
    this.saving = true;
    this.errorMessage = '';
    let request: Observable<CrmTask>;
    if (this.context.task) {
      request = this.api.update(this.context.task.id, { title: value.title, dueAt, ownerId });
    } else {
      const fixed = this.context.related;
      const related = fixed ? { type: fixed.type, id: fixed.id } : { type: 'customer' as const, id: value.contact?.id ?? '' };
      request = this.api.create({ title: value.title, dueAt, related, ownerId });
    }
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (saved) => {
        this.saving = false;
        this.activeModal.close(saved);
      },
      error: (err: CrmApiError) => {
        this.saving = false;
        const f = err.fieldErrors;
        this.serverErrors = { title: f['title'], dueAt: f['dueAt'], ownerId: f['ownerId'], related: f['customerId'] ?? f['opportunityId'] };
        this.conflict = err.status === 409;
        this.errorMessage = Object.values(this.serverErrors).some(Boolean) ? '' : err.message;
      },
    });
  }

  private searchCustomers(term: string): Observable<CrmContact[]> {
    return this.customersApi.list({ search: term, pageSize: SEARCH_PAGE_SIZE }).pipe(
      map((page) => page.results.map((c) => ({ id: c.id, name: c.name, phone: c.phone }))),
      catchError(() => of([])),
    );
  }
}
