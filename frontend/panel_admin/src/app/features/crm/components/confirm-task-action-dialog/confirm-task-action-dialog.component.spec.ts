import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { makeTask } from '../../testing/crm-fixtures';
import { ConfirmTaskActionDialogComponent } from './confirm-task-action-dialog.component';

describe('ConfirmTaskActionDialogComponent', () => {
  let fixture: ComponentFixture<ConfirmTaskActionDialogComponent>;
  let modal: jasmine.SpyObj<NgbActiveModal>;

  beforeEach(() => {
    modal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    TestBed.configureTestingModule({
      imports: [ConfirmTaskActionDialogComponent],
      providers: [...provideTestTranslations(), { provide: NgbActiveModal, useValue: modal }],
    });
    fixture = TestBed.createComponent(ConfirmTaskActionDialogComponent);
  });

  it('shows the task and closes with true only when confirmed (REV-05)', () => {
    fixture.componentInstance.open('archive', makeTask());
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    expect(root.querySelector('[data-testid="confirm-task-title"]')?.textContent).toContain('Llamar para confirmar pedido');
    expect(modal.close).not.toHaveBeenCalled();
    (root.querySelector('[data-testid="confirm-task-action"]') as HTMLButtonElement).click();
    expect(modal.close).toHaveBeenCalledWith(true);
  });

  it('uses the cancel texts by default', () => {
    fixture.componentInstance.open('cancel', makeTask());
    expect(fixture.componentInstance.keyPrefix).toBe('CRM.CONFIRM_TASK.CANCELAR');
  });
});
