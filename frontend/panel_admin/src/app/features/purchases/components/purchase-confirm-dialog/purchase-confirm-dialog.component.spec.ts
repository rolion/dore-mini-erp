import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';

import { makePurchase } from '../../testing/purchase-fixtures';
import { PurchaseConfirmDialogComponent } from './purchase-confirm-dialog.component';

describe('PurchaseConfirmDialogComponent', () => {
  let fixture: ComponentFixture<PurchaseConfirmDialogComponent>;
  let activeModal: jasmine.SpyObj<NgbActiveModal>;

  beforeEach(async () => {
    activeModal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    await TestBed.configureTestingModule({
      imports: [PurchaseConfirmDialogComponent],
      providers: [{ provide: NgbActiveModal, useValue: activeModal }],
    }).compileComponents();
    fixture = TestBed.createComponent(PurchaseConfirmDialogComponent);
    fixture.componentInstance.init(makePurchase());
    fixture.detectChanges();
  });

  const el = (): HTMLElement => fixture.nativeElement as HTMLElement;
  const byId = (id: string): HTMLElement | null => el().querySelector<HTMLElement>(`[data-testid="${id}"]`);

  it('summarizes the purchase and warns that prices and quantities get locked (AC-15)', () => {
    expect(byId('summary-supplier')?.textContent).toContain('Distribuidora Sur');
    expect(byId('summary-count')?.textContent).toContain('1');
    expect(byId('summary-total')?.textContent).toContain('Bs 25.00');
    expect(byId('lock-warning')?.textContent).toContain('precios y las cantidades quedan bloqueados');
    expect(el().textContent).toContain('Confirmar no modifica las existencias');
  });

  it('closes with true to confirm and dismisses on «Volver» (AC-15)', () => {
    byId('confirm')?.click();
    expect(activeModal.close).toHaveBeenCalledWith(true);
    byId('back')?.click();
    expect(activeModal.dismiss).toHaveBeenCalled();
  });
});
