import { TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { fiscalPeriod } from '../../testing/fiscal-period-fixtures';
import { PeriodStatusDialogComponent } from './period-status-dialog.component';

describe('PeriodStatusDialogComponent', () => {
  function create(action: 'close' | 'reopen') {
    const activeModal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    TestBed.configureTestingModule({
      imports: [PeriodStatusDialogComponent],
      providers: [...provideTestTranslations(), { provide: NgbActiveModal, useValue: activeModal }],
    });
    const fixture = TestBed.createComponent(PeriodStatusDialogComponent);
    fixture.componentInstance.period = fiscalPeriod();
    fixture.componentInstance.action = action;
    fixture.detectChanges();
    return { fixture, activeModal };
  }

  it('explains that closing creates no closing entries and can be undone', () => {
    const { fixture } = create('close');
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Año 2026');
    expect(text).toContain('no genera asientos de cierre');
  });

  it('confirms with true', () => {
    const { fixture, activeModal } = create('reopen');
    fixture.nativeElement.querySelector('button.btn-primary').click();
    expect(activeModal.close).toHaveBeenCalledWith(true);
  });
});
