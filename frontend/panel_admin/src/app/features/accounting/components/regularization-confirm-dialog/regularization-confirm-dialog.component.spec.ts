import { TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { RegularizationConfirmDialogComponent } from './regularization-confirm-dialog.component';

describe('RegularizationConfirmDialogComponent', () => {
  it('states what will be created and what it does not change, and confirms with true (UI-04)', () => {
    const activeModal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    TestBed.configureTestingModule({
      imports: [RegularizationConfirmDialogComponent],
      providers: [...provideTestTranslations(), { provide: NgbActiveModal, useValue: activeModal }],
    });
    const fixture = TestBed.createComponent(RegularizationConfirmDialogComponent);
    fixture.componentInstance.count = 3;
    fixture.componentInstance.amounts = 'Bs 175.00';
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('[data-testid="summary"]')?.textContent).toContain('3');
    expect(el.querySelector('[data-testid="summary"]')?.textContent).toContain('Bs 175.00');
    expect(el.textContent).toContain('No modifica pagos');
    (el.querySelector('[data-testid="confirm"]') as HTMLButtonElement).click();
    expect(activeModal.close).toHaveBeenCalledWith(true);
  });
});
