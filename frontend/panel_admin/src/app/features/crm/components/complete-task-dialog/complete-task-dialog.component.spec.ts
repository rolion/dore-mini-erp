import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { CrmApiError } from '../../models/board';
import { CrmTasksApiService } from '../../services/crm-tasks-api.service';
import { makeActivity, makeTask } from '../../testing/crm-fixtures';
import { CompleteTaskDialogComponent } from './complete-task-dialog.component';

describe('CompleteTaskDialogComponent', () => {
  let fixture: ComponentFixture<CompleteTaskDialogComponent>;
  let component: CompleteTaskDialogComponent;
  let api: jasmine.SpyObj<CrmTasksApiService>;
  let modal: jasmine.SpyObj<NgbActiveModal>;

  beforeEach(() => {
    api = jasmine.createSpyObj<CrmTasksApiService>('CrmTasksApiService', ['complete']);
    modal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    TestBed.configureTestingModule({
      imports: [CompleteTaskDialogComponent],
      providers: [...provideTestTranslations(), { provide: CrmTasksApiService, useValue: api }, { provide: NgbActiveModal, useValue: modal }],
    });
    fixture = TestBed.createComponent(CompleteTaskDialogComponent);
    component = fixture.componentInstance;
    component.open(makeTask());
    fixture.detectChanges();
  });

  it('completes without activity by default (AC-03)', () => {
    const result = { task: makeTask({ status: 'done' }), activity: null };
    api.complete.and.returnValue(of(result));
    component.confirm();
    expect(api.complete).toHaveBeenCalledWith('t-1', undefined);
    expect(modal.close).toHaveBeenCalledWith(result);
  });

  it('completes through the real form submit, never as a native page submit (page-reload regression)', () => {
    api.complete.and.returnValue(of({ task: makeTask({ status: 'done' }), activity: null }));
    const submit = new Event('submit', { cancelable: true });
    (fixture.nativeElement as HTMLElement).querySelector('form')!.dispatchEvent(submit);
    expect(submit.defaultPrevented).toBeTrue();
    expect(api.complete).toHaveBeenCalledTimes(1);
  });

  it('requires an outcome or notes before sending the optional activity (AC-03)', () => {
    component.withActivity.setValue(true);
    fixture.detectChanges();
    expect(component.canConfirm).toBeFalse();
    component.form.controls.notes.setValue('Atendió');
    expect(component.canConfirm).toBeTrue();
    api.complete.and.returnValue(of({ task: makeTask({ status: 'done' }), activity: makeActivity() }));
    component.confirm();
    expect(api.complete).toHaveBeenCalledWith('t-1', { channel: 'call', outcome: '', notes: 'Atendió' });
  });

  it('shows a warning with the server message on a 409 and keeps the dialog open', () => {
    api.complete.and.returnValue(throwError(() => new CrmApiError('Ya está completada.', 409)));
    component.confirm();
    fixture.detectChanges();
    expect(modal.close).not.toHaveBeenCalled();
    expect(component.conflict).toBeTrue();
    expect((fixture.nativeElement as HTMLElement).querySelector('[data-testid="complete-error"]')?.textContent).toContain('Ya está completada.');
  });
});
