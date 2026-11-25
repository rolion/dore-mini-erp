import { provideTestTranslations } from '../../../../core/i18n/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { of, throwError } from 'rxjs';
import { CrmApiError } from '../../models/board';
import { CrmOpportunity } from '../../models/opportunity';
import { CrmOpportunitiesApiService } from '../../services/crm-opportunities-api.service';
import { makeOpportunity } from '../../testing/crm-fixtures';
import { CLOSE_DIALOG_CONVERT, CloseOpportunityDialogComponent } from './close-opportunity-dialog.component';

describe('CloseOpportunityDialogComponent', () => {
  let fixture: ComponentFixture<CloseOpportunityDialogComponent>;
  let component: CloseOpportunityDialogComponent;
  let api: jasmine.SpyObj<CrmOpportunitiesApiService>;
  let modal: jasmine.SpyObj<NgbActiveModal>;
  const withCustomer = makeOpportunity({ customer: { id: 'c-1', name: 'Carla', phone: '7' } });

  function setup(opportunity: CrmOpportunity, salesEnabled = true): void {
    api = jasmine.createSpyObj<CrmOpportunitiesApiService>('CrmOpportunitiesApiService', ['close', 'setOrder', 'linkableOrders']);
    api.linkableOrders.and.returnValue(of([{ id: 'p-1', orderDate: '2026-11-21', total: '150.00', status: 'DELIVERED' }]));
    modal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    TestBed.configureTestingModule({
      imports: [CloseOpportunityDialogComponent],
      providers: [...provideTestTranslations(), { provide: CrmOpportunitiesApiService, useValue: api },
        { provide: NgbActiveModal, useValue: modal }],
    });
    fixture = TestBed.createComponent(CloseOpportunityDialogComponent);
    component = fixture.componentInstance;
    component.open(opportunity, salesEnabled);
    fixture.detectChanges();
  }

  const el = (): HTMLElement => fixture.nativeElement as HTMLElement;
  const confirmButton = (): HTMLButtonElement => el().querySelector('[data-testid="confirm-close"]') as HTMLButtonElement;
  const pick = (testId: string): void => {
    (el().querySelector(`[data-testid="${testId}"]`) as HTMLInputElement).click();
    fixture.detectChanges();
  };

  it('requires a trimmed reason to close as lost and sends it (AC-04)', () => {
    setup(makeOpportunity());
    expect(confirmButton().disabled).toBeTrue();
    pick('result-lost');
    expect(confirmButton().disabled).toBeTrue();
    expect(confirmButton().classList).toContain('btn-danger');
    component.form.controls.lostReason.setValue('   ');
    fixture.detectChanges();
    expect(confirmButton().disabled).toBeTrue();
    const closed = makeOpportunity({ status: 'lost' });
    api.close.and.returnValue(of(closed));
    component.form.controls.lostReason.setValue('  Precio alto ');
    fixture.detectChanges();
    expect(el().textContent).toContain('14 / 500');
    confirmButton().click();
    expect(api.close).toHaveBeenCalledOnceWith('o-1', { result: 'lost', lostReason: 'Precio alto' });
    expect(modal.close).toHaveBeenCalledWith(closed);
  });

  it('closes as won with an optional order of the same customer when Sales is enabled (AC-04, AC-06)', () => {
    setup(withCustomer);
    pick('result-won');
    expect(api.linkableOrders).toHaveBeenCalledOnceWith('o-1');
    expect(el().querySelector('[data-testid="order-picker"]')?.textContent).toContain('Bs 150.00');
    api.close.and.returnValue(of(makeOpportunity({ status: 'won' })));
    component.form.controls.orderId.setValue('p-1');
    confirmButton().click();
    expect(api.close).toHaveBeenCalledOnceWith('o-1', { result: 'won', orderId: 'p-1' });
  });

  it('closes as won without an order and hides the order picker when Sales is disabled', () => {
    setup(withCustomer, false);
    pick('result-won');
    expect(api.linkableOrders).not.toHaveBeenCalled();
    expect(el().querySelector('[data-testid="order-picker"]')).toBeNull();
    api.close.and.returnValue(of(makeOpportunity({ status: 'won' })));
    confirmButton().click();
    expect(api.close).toHaveBeenCalledOnceWith('o-1', { result: 'won', orderId: undefined });
  });

  it('offers to convert the lead before linking an order when there is no customer', () => {
    setup(makeOpportunity());
    pick('result-won');
    expect(api.linkableOrders).not.toHaveBeenCalled();
    expect(el().querySelector('[data-testid="needs-conversion"]')).not.toBeNull();
    pick('go-convert');
    expect(modal.dismiss).toHaveBeenCalledWith(CLOSE_DIALOG_CONVERT);
  });

  it('shows a 409 as a warning inside the dialog and keeps the reason (already_closed)', () => {
    setup(makeOpportunity());
    pick('result-lost');
    api.close.and.returnValue(throwError(() => new CrmApiError('Ya se cerró como ganada.', 409, {}, 'already_closed')));
    component.form.controls.lostReason.setValue('Precio');
    fixture.detectChanges();
    confirmButton().click();
    fixture.detectChanges();
    const alert = el().querySelector('[data-testid="close-error"]');
    expect(alert?.classList).toContain('alert-warning');
    expect(alert?.textContent).toContain('Ya se cerró como ganada.');
    expect(component.form.controls.lostReason.value).toBe('Precio');
    expect(modal.close).not.toHaveBeenCalled();
  });

  it('links an order to an already won opportunity', () => {
    setup(makeOpportunity({ status: 'won', customer: { id: 'c-1', name: 'Carla', phone: '7' } }));
    expect(el().textContent).toContain('Vincular pedido');
    expect(el().querySelector('[data-testid="result-lost"]')).toBeNull();
    expect(confirmButton().disabled).toBeTrue();
    api.setOrder.and.returnValue(throwError(() => new CrmApiError('Pedido ya vinculado.', 409, {}, 'order_already_linked')));
    component.form.controls.orderId.setValue('p-1');
    fixture.detectChanges();
    confirmButton().click();
    fixture.detectChanges();
    expect(api.setOrder).toHaveBeenCalledOnceWith('o-1', 'p-1');
    expect(el().textContent).toContain('Pedido ya vinculado.');
  });
});
