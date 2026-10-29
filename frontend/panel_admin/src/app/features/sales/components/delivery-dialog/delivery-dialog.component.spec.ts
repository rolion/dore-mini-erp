import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { Subject, of, throwError } from 'rxjs';
import { Order, OrderApiError, OrderRuleError } from '../../models/order';
import { OrdersApiService } from '../../services/orders-api.service';
import { makeDeliveryLine, makeOrder, makePreview } from '../../testing/order-fixtures';
import { DeliveryDialogComponent, STALE_ORDER } from './delivery-dialog.component';

describe('DeliveryDialogComponent', () => {
  let fixture: ComponentFixture<DeliveryDialogComponent>;
  let component: DeliveryDialogComponent;
  let api: jasmine.SpyObj<OrdersApiService>;
  let modal: jasmine.SpyObj<NgbActiveModal>;
  const order = makeOrder({ status: 'READY', allowedTransitions: ['deliver', 'cancel'] });
  const delivered = makeOrder({ status: 'DELIVERED', allowedTransitions: [] });

  function setup(preview = makePreview()): HTMLElement {
    fixture = TestBed.createComponent(DeliveryDialogComponent);
    component = fixture.componentInstance;
    component.init(order, preview);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  function q(id: string): HTMLElement | null {
    return (fixture.nativeElement as HTMLElement).querySelector(`[data-testid="${id}"]`);
  }

  function confirmButton(): HTMLButtonElement {
    return q('confirm') as HTMLButtonElement;
  }

  beforeEach(() => {
    api = jasmine.createSpyObj<OrdersApiService>('OrdersApiService', ['deliver', 'deliveryPreview']);
    modal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    TestBed.configureTestingModule({
      imports: [DeliveryDialogComponent],
      providers: [
        { provide: OrdersApiService, useValue: api },
        { provide: NgbActiveModal, useValue: modal },
      ],
    });
  });

  it('shows the order, the only warehouse preselected and the table with projected balance (UI-02, AC-14)', () => {
    setup();
    expect(q('order-reference')?.textContent).toContain('P-1A2B3C4D');
    expect(q('warehouse-fixed')?.textContent).toContain('Central');
    expect(q('warehouse-select')).toBeNull();
    const cells = Array.from(q('line-row')!.querySelectorAll('td')).map((td) => td.textContent?.replace(/\s+/g, ' ').trim());
    expect(cells).toEqual(['Bolsas', '4', 'u', '5', '1']);
    expect(q('alert-insufficient')).toBeNull();
    expect(q('alert-negative')).toBeNull();
    expect(confirmButton().disabled).toBeFalse();
  });

  it('offers a selector when there are several warehouses and preloads the suggested one (UI-02)', () => {
    setup(makePreview({
      warehouses: [{ id: 'w-1', name: 'Central', isDefault: true }, { id: 'w-2', name: 'Zona', isDefault: false }],
    }));
    const select = q('warehouse-select') as HTMLSelectElement;
    expect(select.value).toBe('w-1');
    expect(select.textContent).toContain('Central (predeterminado)');
  });

  it('reloads the table for the chosen warehouse (UI-02)', () => {
    api.deliveryPreview.and.returnValue(of(makePreview({
      warehouseId: 'w-2', lines: [makeDeliveryLine({ available: '9.0000', projected: '5.0000' })],
    })));
    setup(makePreview({
      warehouses: [{ id: 'w-1', name: 'Central', isDefault: true }, { id: 'w-2', name: 'Zona', isDefault: false }],
    }));
    component.form.controls.warehouseId.setValue('w-2');
    fixture.detectChanges();
    expect(api.deliveryPreview).toHaveBeenCalledOnceWith('o-1', 'w-2');
    expect(q('line-row')!.textContent).toContain('9');
  });

  it('blocks the confirmation and explains the shortage with a blocked policy (UI-03, AC-02)', () => {
    setup(makePreview({
      lines: [makeDeliveryLine({ available: '1.0000', projected: '-3.0000', insufficient: true })],
    }));
    const alert = q('alert-insufficient')!;
    expect(alert.textContent).toContain('Existencia insuficiente en Central');
    expect(alert.textContent).toContain('solicitado 4 u, existencia 1 u');
    expect(q('alert-negative')).toBeNull();
    expect(confirmButton().disabled).toBeTrue();
    component.confirm();
    expect(api.deliver).not.toHaveBeenCalled();
  });

  it('warns but allows the confirmation when negative stock is permitted (UI-03, AC-03)', () => {
    setup(makePreview({
      allowNegativeStock: true,
      lines: [makeDeliveryLine({ available: '1.0000', projected: '-3.0000', insufficient: true })],
    }));
    expect(q('alert-negative')?.textContent).toContain('saldo negativo en 1 producto');
    expect(q('alert-insufficient')).toBeNull();
    expect(confirmButton().disabled).toBeFalse();
  });

  it('explains what is missing and blocks when the company has no active warehouse (UI-03, AC-07)', () => {
    setup(makePreview({ warehouses: [], warehouseId: null, lines: [] }));
    expect(q('alert-no-warehouse')?.textContent).toContain('Inventario → Configuración → Almacenes');
    expect(q('lines-table')).toBeNull();
    expect(confirmButton().disabled).toBeTrue();
  });

  it('requires a warehouse to be chosen when none is suggested (AC-07)', () => {
    setup(makePreview({
      warehouseId: null,
      warehouses: [{ id: 'w-1', name: 'A', isDefault: false }, { id: 'w-2', name: 'B', isDefault: false }],
    }));
    expect(confirmButton().disabled).toBeTrue();
  });

  it('confirms with the date and warehouse and closes returning the delivered order (AC-01)', () => {
    api.deliver.and.returnValue(of(delivered));
    setup();
    component.form.controls.deliveredDate.setValue('2026-10-03');
    component.confirm();
    expect(api.deliver).toHaveBeenCalledOnceWith('o-1', '2026-10-03', 'w-1');
    expect(modal.close).toHaveBeenCalledOnceWith(delivered);
  });

  it('disables the button while sending so a double click cannot deliver twice (UI-04, AC-04)', () => {
    const pending = new Subject<Order>();
    api.deliver.and.returnValue(pending);
    setup();
    component.confirm();
    fixture.detectChanges();
    expect(confirmButton().disabled).toBeTrue();
    expect(confirmButton().textContent).toContain('Confirmando');
    expect((q('cancel') as HTMLButtonElement).disabled).toBeTrue();
    component.confirm();
    expect(api.deliver).toHaveBeenCalledTimes(1);
    pending.next(delivered);
    pending.complete();
    fixture.detectChanges();
    expect(component.saving).toBeFalse();
  });

  it('keeps the dialog and the chosen data and shows the current balances after a 409 insufficient_stock (UI-04, AC-02)', () => {
    api.deliver.and.returnValue(throwError(() => new OrderRuleError(
      'No hay saldo suficiente para registrar la salida.', 'insufficient_stock',
      [{ productName: 'Bolsas', unit: 'u', requested: '4.0000', available: '1.0000' }], 'Central')));
    api.deliveryPreview.and.returnValue(of(makePreview({
      lines: [makeDeliveryLine({ available: '1.0000', projected: '-3.0000', insufficient: true })],
    })));
    setup();
    component.form.controls.deliveredDate.setValue('2026-10-03');
    component.confirm();
    fixture.detectChanges();
    expect(modal.close).not.toHaveBeenCalled();
    expect(modal.dismiss).not.toHaveBeenCalled();
    expect(component.form.controls.deliveredDate.value).toBe('2026-10-03');
    expect(q('alert-error')?.textContent).toContain('No hay saldo suficiente');
    expect(q('alert-insufficient')).not.toBeNull();
    expect(confirmButton().disabled).toBeTrue();
    expect(api.deliveryPreview).toHaveBeenCalledOnceWith('o-1', 'w-1');
  });

  it('shows warehouse errors from the server under the field (AC-07)', () => {
    api.deliver.and.returnValue(throwError(() => new OrderApiError('Revisa los datos ingresados.', 400, {
      warehouseId: ['El almacén está inactivo.'],
    })));
    setup();
    component.confirm();
    fixture.detectChanges();
    expect(q('warehouse-error')?.textContent).toContain('El almacén está inactivo.');
    expect(modal.close).not.toHaveBeenCalled();
  });

  it('dismisses as stale when the order already changed elsewhere (EDGE-01)', () => {
    api.deliver.and.returnValue(throwError(() => new OrderRuleError('Esa acción no está permitida.', 'invalid_transition')));
    setup();
    component.confirm();
    expect(modal.dismiss).toHaveBeenCalledOnceWith(STALE_ORDER);
  });

  it('shows any other error and keeps the data', () => {
    api.deliver.and.returnValue(throwError(() => new OrderApiError('No se pudo conectar con el servidor.', 0)));
    setup();
    component.confirm();
    fixture.detectChanges();
    expect(q('alert-error')?.textContent).toContain('No se pudo conectar');
    expect(component.saving).toBeFalse();
    expect(confirmButton().disabled).toBeFalse();
  });

  it('cancels without touching the order (UI-04)', () => {
    setup();
    (q('cancel') as HTMLButtonElement).click();
    expect(modal.dismiss).toHaveBeenCalled();
    expect(api.deliver).not.toHaveBeenCalled();
  });
});
