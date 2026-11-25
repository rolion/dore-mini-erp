import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { provideRouter } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { AuthService } from '../../../../core/service/auth.service';
import { CrmApiError } from '../../models/board';
import { CrmTasksApiService } from '../../services/crm-tasks-api.service';
import { CrmUsersApiService } from '../../services/crm-users-api.service';
import { makeTask } from '../../testing/crm-fixtures';
import { CrmTaskListComponent } from './crm-task-list.component';

describe('CrmTaskListComponent', () => {
  let fixture: ComponentFixture<CrmTaskListComponent>;
  let component: CrmTaskListComponent;
  let api: jasmine.SpyObj<CrmTasksApiService>;
  let modal: jasmine.SpyObj<NgbModal>;
  const pending = makeTask();
  const overdue = makeTask({ id: 't-2', title: 'Cobrar saldo', isOverdue: true });
  const done = makeTask({ id: 't-3', title: 'Enviar catálogo', status: 'done', completedAt: '2026-11-25T12:00:00Z' });

  async function setup(rows = [pending, overdue, done]): Promise<void> {
    api = jasmine.createSpyObj<CrmTasksApiService>('CrmTasksApiService', ['list', 'cancel', 'reopen', 'archive']);
    api.list.and.returnValue(of({ count: rows.length, results: rows }));
    modal = jasmine.createSpyObj<NgbModal>('NgbModal', ['open']);
    await TestBed.configureTestingModule({
      imports: [CrmTaskListComponent],
      providers: [
        ...provideTestTranslations(), provideRouter([]),
        { provide: CrmTasksApiService, useValue: api },
        { provide: CrmUsersApiService, useValue: { list: () => of([{ id: 8, name: 'Beto' }]) } },
        { provide: AuthService, useValue: { currentUserValue: { id: 7, username: 'ana', firstName: 'Ana', lastName: 'Admin' } } },
        { provide: NgbModal, useValue: modal },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(CrmTaskListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  }

  const text = (): string => (fixture.nativeElement as HTMLElement).textContent ?? '';
  const query = (selector: string): HTMLElement | null => fixture.debugElement.query(By.css(selector))?.nativeElement ?? null;

  it('loads my pending tasks by default and shows overdue and done states (AC-09)', async () => {
    await setup();
    expect(api.list).toHaveBeenCalledWith({ ownerId: 7, status: 'pending', page: 1, pageSize: 10 });
    const badges = fixture.debugElement.queryAll(By.css('[data-testid="status-badge"]')).map((b) => (b.nativeElement as HTMLElement).textContent?.trim());
    expect(badges).toEqual(['Pendiente', 'Vencida', 'Hecha']);
    expect(text()).toContain('Cobrar saldo');
  });

  it('offers actions by state: complete/edit/cancel for pending, reopen/archive otherwise (AC-09)', async () => {
    await setup([pending, done]);
    const rows = fixture.debugElement.queryAll(By.css('[data-testid="task-row"]'));
    const testIds = (row: number): string[] => rows[row].queryAll(By.css('button')).map((b) => (b.nativeElement as HTMLElement).dataset['testid'] ?? '');
    expect(testIds(0)).toEqual(['complete-task', 'edit-task', 'cancel-task']);
    expect(testIds(1)).toEqual(['reopen-task', 'archive-task']);
  });

  it('reloads from page 1 when a filter changes, and clears them (AC-05, AC-09)', async () => {
    await setup();
    api.list.calls.reset();
    component.statusControl.setValue('overdue');
    expect(api.list).toHaveBeenCalledWith({ ownerId: 7, status: 'overdue', page: 1, pageSize: 10 });
    component.ownerControl.setValue('');
    expect(api.list).toHaveBeenCalledWith({ ownerId: undefined, status: 'overdue', page: 1, pageSize: 10 });
    component.clearFilters();
    expect(api.list).toHaveBeenCalledWith({ ownerId: undefined, status: 'pending', page: 1, pageSize: 10 });
  });

  it('shows the empty state with a create button and the no-results state with filters (UI-03)', async () => {
    await setup([]);
    component.clearFilters();
    fixture.detectChanges();
    expect(query('[data-testid="empty-new"]')).not.toBeNull();
    component.statusControl.setValue('done');
    fixture.detectChanges();
    expect(query('[data-testid="empty-clear"]')).not.toBeNull();
  });

  it('shows the error with retry (UI-03)', async () => {
    await setup();
    api.list.and.returnValue(throwError(() => new CrmApiError('Sin conexión', 0)));
    component.retry();
    fixture.detectChanges();
    expect(query('[data-testid="task-error"]')?.textContent).toContain('Sin conexión');
    expect(query('[data-testid="retry"]')).not.toBeNull();
  });

  it('asks for confirmation before cancelling or archiving, then calls the API and reloads (AC-04, REV-05)', async () => {
    await setup([pending, done]);
    api.cancel.and.returnValue(of(makeTask({ status: 'cancelled' })));
    api.reopen.and.returnValue(of(pending));
    api.archive.and.returnValue(of(makeTask({ status: 'archived' })));
    const dialog = jasmine.createSpyObj('ConfirmTaskActionDialogComponent', ['open']);
    modal.open.and.returnValue({ componentInstance: dialog, result: Promise.resolve(true) } as never);
    api.list.calls.reset();
    component.cancel(pending);
    component.archive(done);
    expect(api.cancel).not.toHaveBeenCalled();
    expect(api.archive).not.toHaveBeenCalled();
    await fixture.whenStable();
    expect(dialog.open).toHaveBeenCalledWith('cancel', pending);
    expect(dialog.open).toHaveBeenCalledWith('archive', done);
    expect(api.cancel).toHaveBeenCalledWith('t-1');
    expect(api.archive).toHaveBeenCalledWith('t-3');
    component.reopen(done);
    expect(api.reopen).toHaveBeenCalledWith('t-3');
    expect(api.list).toHaveBeenCalledTimes(3);
  });

  it('does nothing when the confirmation is dismissed (REV-05)', async () => {
    await setup([pending]);
    modal.open.and.returnValue({ componentInstance: jasmine.createSpyObj('D', ['open']), result: Promise.reject('x') } as never);
    component.cancel(pending);
    await fixture.whenStable();
    expect(api.cancel).not.toHaveBeenCalled();
  });

  it('shows a 409 from an action as an error and reloads (UI-03)', async () => {
    await setup();
    api.cancel.and.returnValue(throwError(() => new CrmApiError('Ya no está pendiente.', 409)));
    modal.open.and.returnValue({ componentInstance: jasmine.createSpyObj('D', ['open']), result: Promise.resolve(true) } as never);
    component.cancel(pending);
    await fixture.whenStable();
    fixture.detectChanges();
    expect(component.actionError).toBe('Ya no está pendiente.');
    expect(query('[data-testid="action-error"]')?.textContent).toContain('Ya no está pendiente.');
  });

  it('opens the create dialog with owners and the current user (AC-01)', async () => {
    await setup();
    const dialog = jasmine.createSpyObj('TaskDialogComponent', ['open']);
    modal.open.and.returnValue({ componentInstance: dialog, result: Promise.resolve(pending) } as never);
    component.create();
    await fixture.whenStable();
    expect(dialog.open).toHaveBeenCalledWith({ owners: jasmine.any(Array), currentUser: { id: 7, name: 'Ana Admin' } });
    expect(component.success).toBe('Tarea creada.');
  });
});
