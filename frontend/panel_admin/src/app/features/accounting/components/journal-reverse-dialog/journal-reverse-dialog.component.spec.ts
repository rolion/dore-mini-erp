import { TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { AccountingApiError } from '../../models/accounting';
import { JournalApiService } from '../../services/journal-api.service';
import { makeJournalDetail } from '../../testing/journal-fixtures';
import { JournalReverseDialogComponent } from './journal-reverse-dialog.component';

describe('JournalReverseDialogComponent', () => {
  function create(reverse = of(makeJournalDetail({ id: 'j-2' }))) {
    const api = jasmine.createSpyObj<JournalApiService>('JournalApiService', ['reverse']);
    api.reverse.and.returnValue(reverse);
    const modal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    TestBed.configureTestingModule({
      imports: [JournalReverseDialogComponent],
      providers: [...provideTestTranslations(), { provide: JournalApiService, useValue: api }, { provide: NgbActiveModal, useValue: modal }],
    });
    const fixture = TestBed.createComponent(JournalReverseDialogComponent);
    fixture.componentInstance.init(makeJournalDetail());
    fixture.detectChanges();
    return { fixture, component: fixture.componentInstance, api, modal, el: fixture.nativeElement as HTMLElement };
  }

  it('shows the inverted lines and requires a reason before enabling the button (AC-07)', () => {
    const { fixture, component, el } = create();
    expect(el.querySelectorAll('[data-testid="reverse-lines"] tbody tr').length).toBe(3);
    const button = el.querySelector('[data-testid="confirm-reversal"]') as HTMLButtonElement;
    expect(button.disabled).toBeTrue();
    component.form.controls.reason.setValue('  ');
    fixture.detectChanges();
    expect(button.disabled).toBeTrue();
    component.form.controls.reason.setValue('Error de captura');
    fixture.detectChanges();
    expect(button.disabled).toBeFalse();
  });

  it('reverses with the chosen date and reason and closes with the reversal (AC-07)', () => {
    const { component, api, modal } = create();
    component.form.setValue({ reversalDate: '2026-05-12', reason: ' Error ' });
    component.submit();
    expect(api.reverse).toHaveBeenCalledWith('j-1', '2026-05-12', 'Error');
    expect(modal.close).toHaveBeenCalled();
  });

  it('keeps what was typed and shows the server error inside the dialog (AC-07)', () => {
    const { fixture, component, el, modal } = create(throwError(() => new AccountingApiError('Revisa', 400, { reversal_date: ['Período cerrado'] })));
    component.form.setValue({ reversalDate: '2026-05-12', reason: 'Error' });
    component.submit();
    fixture.detectChanges();
    expect(el.querySelector('[data-testid="date-error"]')?.textContent).toContain('cerrado');
    expect(component.form.controls.reason.value).toBe('Error');
    expect(component.saving).toBeFalse();
    expect(modal.close).not.toHaveBeenCalled();
  });
});
