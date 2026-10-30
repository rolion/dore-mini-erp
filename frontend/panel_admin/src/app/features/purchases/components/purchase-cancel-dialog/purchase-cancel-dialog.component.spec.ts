import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';

import { makeConfirmedPurchase, makePurchase } from '../../testing/purchase-fixtures';
import { PurchaseCancelDialogComponent } from './purchase-cancel-dialog.component';

describe('PurchaseCancelDialogComponent', () => {
  let fixture: ComponentFixture<PurchaseCancelDialogComponent>;
  let component: PurchaseCancelDialogComponent;
  let activeModal: jasmine.SpyObj<NgbActiveModal>;

  beforeEach(async () => {
    activeModal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    await TestBed.configureTestingModule({
      imports: [PurchaseCancelDialogComponent],
      providers: [{ provide: NgbActiveModal, useValue: activeModal }],
    }).compileComponents();
    fixture = TestBed.createComponent(PurchaseCancelDialogComponent);
    component = fixture.componentInstance;
    component.init(makePurchase());
    fixture.detectChanges();
  });

  const el = (): HTMLElement => fixture.nativeElement as HTMLElement;
  const byId = (id: string): HTMLButtonElement | null => el().querySelector<HTMLButtonElement>(`[data-testid="${id}"]`);

  function type(value: string): void {
    component.form.controls.reason.setValue(value);
    fixture.detectChanges();
  }

  it('keeps the button disabled until there is a reason (AC-16)', () => {
    expect(byId('cancel-purchase')?.disabled).toBeTrue();
    type('   ');
    expect(byId('cancel-purchase')?.disabled).toBeTrue();
    type('Pedido duplicado');
    expect(byId('cancel-purchase')?.disabled).toBeFalse();
  });

  it('closes with the trimmed reason (AC-16)', () => {
    type('  Pedido duplicado  ');
    component.submit();
    expect(activeModal.close).toHaveBeenCalledWith('Pedido duplicado');
  });

  it('does not close without a reason and limits it to 500 characters (AC-16)', () => {
    component.submit();
    expect(activeModal.close).not.toHaveBeenCalled();
    type('x'.repeat(501));
    expect(byId('cancel-purchase')?.disabled).toBeTrue();
    expect(el().querySelector('textarea')?.getAttribute('maxlength')).toBe('500');
  });

  it('«Volver» dismisses without changes (AC-16)', () => {
    byId('back')?.click();
    expect(activeModal.dismiss).toHaveBeenCalled();
  });

  it('mentions that a confirmed purchase has no receptions or payments (AC-16)', () => {
    component.init(makeConfirmedPurchase());
    fixture.detectChanges();
    expect(byId('cancel-info')?.textContent).toContain('sin recepciones ni pagos');
  });
});
