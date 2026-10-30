import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';

import { PurchaseApiError } from '../../models/purchase';
import { PurchasesApiService } from '../../services/purchases-api.service';
import { makeCancelledPurchase, makeConfirmedPurchase, makePurchase } from '../../testing/purchase-fixtures';
import { PurchaseDetailComponent } from './purchase-detail.component';

describe('PurchaseDetailComponent', () => {
  let fixture: ComponentFixture<PurchaseDetailComponent>;
  let api: jasmine.SpyObj<PurchasesApiService>;
  let toastr: jasmine.SpyObj<ToastrService>;
  let router: Router;
  let modal: jasmine.SpyObj<NgbModal>;

  async function setup(purchase: ReturnType<typeof makePurchase> | PurchaseApiError): Promise<void> {
    api = jasmine.createSpyObj<PurchasesApiService>('PurchasesApiService', ['get', 'confirm', 'cancel']);
    api.get.and.returnValue(purchase instanceof PurchaseApiError ? throwError(() => purchase) : of(purchase));
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    modal = jasmine.createSpyObj<NgbModal>('NgbModal', ['open']);
    await TestBed.configureTestingModule({
      imports: [PurchaseDetailComponent],
      providers: [
        provideRouter([]),
        { provide: PurchasesApiService, useValue: api },
        { provide: ToastrService, useValue: toastr },
        { provide: NgbModal, useValue: modal },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: 'c-1' }) } } },
      ],
    }).compileComponents();
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    fixture = TestBed.createComponent(PurchaseDetailComponent);
    fixture.detectChanges();
  }

  const text = (): string => (fixture.nativeElement as HTMLElement).textContent ?? '';
  const hrefs = (): (string | null)[] =>
    fixture.debugElement.queryAll(By.css('a')).map((a) => (a.nativeElement as HTMLAnchorElement).getAttribute('href'));

  it('shows the header, the lines with their snapshot and the total (AC-17)', async () => {
    await setup(makePurchase());
    expect(api.get).toHaveBeenCalledWith('c-1');
    for (const expected of ['Distribuidora Sur', '29/10/2026', 'F-100', 'Entrega el martes', 'Borrador', 'BOB', 'Harina', 'kg', '2.500', 'Bs 10.00', 'Bs 25.00']) {
      expect(text()).withContext(expected).toContain(expected);
    }
    expect(fixture.debugElement.queryAll(By.css('[data-testid="item"]')).length).toBe(1);
  });

  const byId = (id: string): HTMLButtonElement | null =>
    (fixture.nativeElement as HTMLElement).querySelector<HTMLButtonElement>(`[data-testid="${id}"]`);

  /** Un diálogo falso que se resuelve (o se descarta) como el usuario lo decida. */
  function dialog(outcome: { close: unknown } | { dismiss: true }): jasmine.SpyObj<{ init: (p: unknown) => void }> {
    const instance = jasmine.createSpyObj<{ init: (p: unknown) => void }>('dialog', ['init']);
    const result = 'close' in outcome ? Promise.resolve(outcome.close) : Promise.reject(new Error('dismissed'));
    modal.open.and.returnValue({ componentInstance: instance, result } as never);
    return instance;
  }
  const flush = (): Promise<void> => new Promise((resolve) => setTimeout(resolve));

  it('shows reference, reception and payment statuses and the Summary tab (AC-13)', async () => {
    await setup(makePurchase());
    expect(text()).toContain('Resumen');
    expect(byId('reference')?.textContent).toContain('COM-1A2B3C4D');
    expect(byId('reception-status')?.textContent).toContain('Sin recibir');
    expect(byId('payment-status')?.textContent).toContain('Sin pagar');
    expect(byId('status-badge')?.className).toContain('col-orange');
    expect(byId('cancel-reason')).toBeNull();
  });

  it('offers Edit, Confirm and Cancel for a draft (AC-14)', async () => {
    await setup(makePurchase());
    expect(hrefs()).toContain('/pocketbiz/purchases/c-1/edit');
    expect(byId('confirm')).not.toBeNull();
    expect(byId('cancel')).not.toBeNull();
    expect(byId('receive')).toBeNull();
  });

  it('offers no editing of a confirmed purchase and shows reception/payment as coming soon (AC-14, AC-17)', async () => {
    await setup(makeConfirmedPurchase());
    expect(hrefs()).not.toContain('/pocketbiz/purchases/c-1/edit');
    expect(byId('confirm')).toBeNull();
    expect(byId('receive')?.disabled).toBeTrue();
    expect(byId('pay')?.disabled).toBeTrue();
    expect(byId('cancel')).not.toBeNull();
    expect(byId('confirmed-at')).not.toBeNull();
    expect(text()).toContain('Sin recibir');
    expect(text()).toContain('Confirmar no modifica las existencias');
    expect(text()).not.toMatch(/aumento de (stock|existencias)/i);
  });

  it('hides Cancel and explains why when the server does not allow it (AC-14)', async () => {
    await setup(makeConfirmedPurchase({ allowedActions: [], receptionStatus: 'partial' }));
    expect(byId('cancel')).toBeNull();
    expect(byId('cancel-blocked')).not.toBeNull();
  });

  it('is read-only when cancelled and shows the reason and date (AC-13, AC-14)', async () => {
    await setup(makeCancelledPurchase());
    expect(byId('cancel-reason')?.textContent).toContain('Pedido duplicado');
    expect(byId('cancelled-at')).not.toBeNull();
    for (const id of ['confirm', 'cancel', 'receive', 'pay']) expect(byId(id)).toBeNull();
    expect(hrefs()).not.toContain('/pocketbiz/purchases/c-1/edit');
    expect(byId('status-badge')?.className).toContain('col-red');
  });

  it('confirms through the dialog and shows the new state (AC-15)', async () => {
    await setup(makePurchase());
    const instance = dialog({ close: true });
    api.confirm.and.returnValue(of(makeConfirmedPurchase()));
    byId('confirm')?.click();
    await flush();
    fixture.detectChanges();
    expect(instance.init).toHaveBeenCalled();
    expect(api.confirm).toHaveBeenCalledWith('c-1');
    expect(toastr.success).toHaveBeenCalledWith('Compra confirmada');
    expect(byId('confirm')).toBeNull();
    expect(byId('receive')).not.toBeNull();
  });

  it('does nothing when the confirmation dialog is dismissed (AC-15)', async () => {
    await setup(makePurchase());
    dialog({ dismiss: true });
    byId('confirm')?.click();
    await flush();
    expect(api.confirm).not.toHaveBeenCalled();
  });

  it('cancels with the reason from the dialog (AC-16)', async () => {
    await setup(makePurchase());
    dialog({ close: 'Pedido duplicado' });
    api.cancel.and.returnValue(of(makeCancelledPurchase()));
    byId('cancel')?.click();
    await flush();
    fixture.detectChanges();
    expect(api.cancel).toHaveBeenCalledWith('c-1', 'Pedido duplicado');
    expect(toastr.success).toHaveBeenCalledWith('Compra cancelada');
    expect(byId('cancel-reason')?.textContent).toContain('Pedido duplicado');
  });

  it('shows the server error and re-reads the purchase after a conflict (EDGE-06)', async () => {
    await setup(makePurchase());
    dialog({ close: true });
    api.confirm.and.returnValue(throwError(() => new PurchaseApiError('Una compra cancelada no puede confirmarse.', 409)));
    api.get.and.returnValue(of(makeCancelledPurchase()));
    byId('confirm')?.click();
    await flush();
    fixture.detectChanges();
    expect(toastr.error).toHaveBeenCalledWith('Una compra cancelada no puede confirmarse.');
    expect(api.get).toHaveBeenCalledTimes(2);
    expect(byId('cancel-reason')).not.toBeNull();
  });

  it('uses fallback texts and still shows an inactive supplier (AC-17)', async () => {
    await setup(makePurchase({ externalReference: '', notes: '', items: [], total: '0.00', supplier: { id: 's-1', name: 'Viejo', active: false } }));
    expect(text()).toContain('Sin referencia');
    expect(text()).toContain('Sin notas');
    expect(text()).toContain('Esta compra aún no tiene productos.');
    expect(text()).toContain('Viejo');
    expect(text()).toContain('Inactivo');
  });

  it('warns and returns to the list when the purchase does not exist (AC-17)', async () => {
    await setup(new PurchaseApiError('Compra no encontrada.', 404));
    expect(toastr.error).toHaveBeenCalledWith('Compra no encontrada.');
    expect(router.navigate).toHaveBeenCalledWith(['/pocketbiz/purchases']);
  });
});
