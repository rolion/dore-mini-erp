import { TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { DeactivateDialogComponent } from './deactivate-dialog.component';

describe('DeactivateDialogComponent', () => {
  function create(methods: string[]) {
    const activeModal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    TestBed.configureTestingModule({
      imports: [DeactivateDialogComponent],
      providers: [...provideTestTranslations(), { provide: NgbActiveModal, useValue: activeModal }],
    });
    const fixture = TestBed.createComponent(DeactivateDialogComponent);
    fixture.componentInstance.account = { id: 'a1', name: 'Banco', currency: 'BOB', isActive: true };
    fixture.componentInstance.methods = methods;
    fixture.detectChanges();
    return { fixture, activeModal, el: fixture.nativeElement as HTMLElement };
  }

  it('asks for confirmation and closes with true (UI-02)', () => {
    const { el, activeModal } = create([]);
    expect(el.querySelector('[data-testid="confirmation"]')?.textContent).toContain('Banco');
    (el.querySelector('.btn-primary') as HTMLButtonElement).click();
    expect(activeModal.close).toHaveBeenCalledWith(true);
  });

  it('blocks and lists the active methods that use the account', () => {
    const { el, activeModal } = create(['QR', 'Tarjeta']);
    expect(el.querySelector('[data-testid="blocked"]')?.textContent).toContain('QR, Tarjeta');
    const confirm = el.querySelector('.btn-primary') as HTMLButtonElement;
    expect(confirm.disabled).toBeTrue();
    confirm.click();
    expect(activeModal.close).not.toHaveBeenCalled();
  });
});
