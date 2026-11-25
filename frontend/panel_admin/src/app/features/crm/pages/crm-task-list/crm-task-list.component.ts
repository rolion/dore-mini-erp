import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgbModal, NgbPagination } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { Subject, catchError, of, switchMap } from 'rxjs';
import { tr } from '../../../../core/i18n/translate';
import { AuthService } from '../../../../core/service/auth.service';
import { CompleteTaskDialogComponent } from '../../components/complete-task-dialog/complete-task-dialog.component';
import { TaskDialogComponent } from '../../components/task-dialog/task-dialog.component';
import { CrmApiError } from '../../models/board';
import { CrmOwner } from '../../models/opportunity';
import { CrmTask, CrmTaskFilter } from '../../models/task';
import { CrmTaskCompletion, CrmTasksApiService } from '../../services/crm-tasks-api.service';
import { CrmUsersApiService } from '../../services/crm-users-api.service';

/** `''` = todos los responsables; si no, el id del usuario. */
export type OwnerFilter = '' | string;

export const TASK_FILTERS: readonly CrmTaskFilter[] = ['pending', 'overdue', 'done', 'cancelled', 'all'];

/** CRM › Por contactar: tareas por responsable, vencimiento y estado, con las acciones de cada estado. */
@Component({
  selector: 'app-crm-task-list',
  templateUrl: './crm-task-list.component.html',
  styleUrl: './crm-task-list.component.scss',
  imports: [TranslatePipe, RouterLink, ReactiveFormsModule, NgbPagination, DatePipe],
})
export class CrmTaskListComponent implements OnInit {
  readonly pageSize = 10;
  readonly filters = TASK_FILTERS;
  readonly ownerControl = new FormControl<OwnerFilter>('', { nonNullable: true });
  readonly statusControl = new FormControl<CrmTaskFilter>('pending', { nonNullable: true });

  rows: CrmTask[] = [];
  total = 0;
  /** Página actual base 1 (como `ngb-pagination`). */
  page = 1;
  loading = false;
  error = '';
  success = '';
  /** Aviso de una acción rechazada por el servidor (409/400): sobrevive a la recarga de la lista. */
  actionError = '';
  companyUsers: CrmOwner[] = [];

  private api = inject(CrmTasksApiService);
  private usersApi = inject(CrmUsersApiService);
  private auth = inject(AuthService);
  private modal = inject(NgbModal);
  private destroyRef = inject(DestroyRef);
  private reload$ = new Subject<void>();

  get currentUser(): CrmOwner | null {
    const user = this.auth.currentUserValue;
    if (!user) return null;
    const name = `${user.firstName ?? ''} ${user.lastName ?? ''}`.trim() || user.username;
    return { id: user.id, name };
  }

  get hasFilters(): boolean {
    return !!this.ownerControl.value || this.statusControl.value !== 'pending';
  }

  get rangeStart(): number {
    return this.total === 0 ? 0 : (this.page - 1) * this.pageSize + 1;
  }

  get rangeEnd(): number {
    return Math.min(this.page * this.pageSize, this.total);
  }

  ngOnInit(): void {
    const me = this.currentUser;
    if (me) this.ownerControl.setValue(String(me.id), { emitEvent: false });

    this.reload$.pipe(
      switchMap(() => {
        this.loading = true;
        this.error = '';
        const owner = this.ownerControl.value;
        return this.api.list({
          ownerId: owner ? Number(owner) : undefined, status: this.statusControl.value, page: this.page, pageSize: this.pageSize,
        }).pipe(catchError((err: CrmApiError) => {
          this.error = err.message;
          return of(null);
        }));
      }),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe((result) => {
      this.loading = false;
      if (result) {
        this.rows = result.results;
        this.total = result.count;
      }
    });

    this.usersApi.list().pipe(catchError(() => of([] as CrmOwner[])), takeUntilDestroyed(this.destroyRef))
      .subscribe((users) => (this.companyUsers = users));
    for (const control of [this.ownerControl, this.statusControl]) {
      control.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => this.refresh(1));
    }
    this.reload$.next();
  }

  get ownerOptions(): CrmOwner[] {
    const all = new Map<number, CrmOwner>();
    for (const owner of [...this.companyUsers, ...(this.currentUser ? [this.currentUser] : [])]) all.set(owner.id, owner);
    return [...all.values()].sort((a, b) => a.name.localeCompare(b.name));
  }

  clearFilters(): void {
    this.ownerControl.setValue('', { emitEvent: false });
    this.statusControl.setValue('pending', { emitEvent: false });
    this.refresh(1);
  }

  onPage(page: number): void {
    this.refresh(page);
  }

  retry(): void {
    this.reload$.next();
  }

  create(): void {
    const ref = this.modal.open(TaskDialogComponent, { centered: true, backdrop: 'static' });
    (ref.componentInstance as TaskDialogComponent).open({ owners: this.ownerOptions, currentUser: this.currentUser });
    ref.result.then(() => this.done(tr('CRM.TASK_LIST.CREADA')), () => undefined);
  }

  edit(task: CrmTask): void {
    const ref = this.modal.open(TaskDialogComponent, { centered: true, backdrop: 'static' });
    (ref.componentInstance as TaskDialogComponent).open({ owners: this.ownerOptions, currentUser: this.currentUser, task });
    ref.result.then(() => this.done(tr('CRM.TASK_LIST.GUARDADA')), () => this.reload$.next());
  }

  complete(task: CrmTask): void {
    const ref = this.modal.open(CompleteTaskDialogComponent, { centered: true, backdrop: 'static' });
    (ref.componentInstance as CompleteTaskDialogComponent).open(task);
    ref.result.then(
      (result: CrmTaskCompletion) => this.done(tr(result.activity ? 'CRM.TASK_LIST.COMPLETADA_CON_ACTIVIDAD' : 'CRM.TASK_LIST.COMPLETADA')),
      () => this.reload$.next(),
    );
  }

  cancel(task: CrmTask): void {
    this.run(this.api.cancel(task.id), 'CRM.TASK_LIST.CANCELADA_OK');
  }

  reopen(task: CrmTask): void {
    this.run(this.api.reopen(task.id), 'CRM.TASK_LIST.REABIERTA');
  }

  archive(task: CrmTask): void {
    this.run(this.api.archive(task.id), 'CRM.TASK_LIST.ARCHIVADA');
  }

  private run(request: ReturnType<CrmTasksApiService['cancel']>, messageKey: string): void {
    this.success = '';
    this.actionError = '';
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => this.done(tr(messageKey)),
      error: (err: CrmApiError) => {
        this.actionError = err.message;
        this.reload$.next();
      },
    });
  }

  private refresh(page: number): void {
    this.actionError = '';
    this.page = page;
    this.reload$.next();
  }

  private done(message: string): void {
    this.success = message;
    this.reload$.next();
  }
}
