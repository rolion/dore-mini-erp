import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { CrmApiError } from '../../models/board';
import { CrmCustomersApiService } from '../../services/crm-customers-api.service';
import { CrmTasksApiService } from '../../services/crm-tasks-api.service';
import { makeTask } from '../../testing/crm-fixtures';
import { TaskDialogComponent, TaskDialogContext } from './task-dialog.component';

describe('TaskDialogComponent', () => {
  let fixture: ComponentFixture<TaskDialogComponent>;
  let component: TaskDialogComponent;
  let api: jasmine.SpyObj<CrmTasksApiService>;
  let modal: jasmine.SpyObj<NgbActiveModal>;
  const me = { id: 7, name: 'Ana Admin' };

  function setup(context: Partial<TaskDialogContext> = {}): void {
    api = jasmine.createSpyObj<CrmTasksApiService>('CrmTasksApiService', ['create', 'update']);
    modal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    TestBed.configureTestingModule({
      imports: [TaskDialogComponent],
      providers: [...provideTestTranslations(), { provide: CrmTasksApiService, useValue: api },
        { provide: CrmCustomersApiService, useValue: jasmine.createSpyObj('CrmCustomersApiService', ['list']) },
        { provide: NgbActiveModal, useValue: modal }],
    });
    fixture = TestBed.createComponent(TaskDialogComponent);
    component = fixture.componentInstance;
    component.open({ owners: [me], currentUser: me, ...context });
    fixture.detectChanges();
  }

  it('creates a task for a fixed related entity with the current user as default owner (AC-01)', () => {
    setup({ related: { type: 'opportunity', id: 'o-1', name: 'Combo' } });
    component.form.patchValue({ title: ' Llamar ', dueAt: '2026-11-26T15:00' });
    api.create.and.returnValue(of(makeTask()));
    component.onSubmit();
    const call = api.create.calls.mostRecent().args[0];
    expect([call.title, call.related, call.ownerId]).toEqual([' Llamar ', { type: 'opportunity', id: 'o-1' }, 7]);
    expect(call.dueAt).toBe(new Date('2026-11-26T15:00').toISOString());
    expect(modal.close).toHaveBeenCalled();
  });

  it('requires title, due date and, without a fixed related, a customer (AC-01)', () => {
    setup();
    component.onSubmit();
    expect(api.create).not.toHaveBeenCalled();
    expect(component.form.controls.contact.invalid).toBeTrue();
    expect(component.form.controls.title.invalid).toBeTrue();
    expect(component.form.controls.dueAt.invalid).toBeTrue();
    component.form.patchValue({ contact: { id: 'c-1', name: 'Ana', phone: '' }, title: 'x', dueAt: '2026-11-26T15:00' });
    api.create.and.returnValue(of(makeTask()));
    component.onSubmit();
    expect(api.create.calls.mostRecent().args[0].related).toEqual({ type: 'customer', id: 'c-1' });
  });

  it('edits a pending task without changing its related entity (AC-06)', () => {
    setup({ task: makeTask() });
    expect(component.choosesRelated).toBeFalse();
    expect(component.form.controls.title.value).toBe('Llamar para confirmar pedido');
    component.form.patchValue({ title: 'Visitar' });
    api.update.and.returnValue(of(makeTask({ title: 'Visitar' })));
    component.onSubmit();
    expect(api.update.calls.mostRecent().args[0]).toBe('t-1');
    expect(api.update.calls.mostRecent().args[1].title).toBe('Visitar');
  });

  it('shows a warning on 409 and field errors on 400 (AC-02)', () => {
    setup({ related: { type: 'customer', id: 'c-1', name: 'Ana' } });
    component.form.patchValue({ title: 'x', dueAt: '2026-11-26T15:00' });
    api.create.and.returnValue(throwError(() => new CrmApiError('El cliente está inactivo.', 409)));
    component.onSubmit();
    expect(component.conflict).toBeTrue();
    expect(component.errorMessage).toBe('El cliente está inactivo.');
    api.create.and.returnValue(throwError(() => new CrmApiError('Datos inválidos', 400, { title: 'Ingresa un título.' })));
    component.onSubmit();
    expect(component.serverErrors.title).toBe('Ingresa un título.');
    expect(component.errorMessage).toBe('');
  });
});
