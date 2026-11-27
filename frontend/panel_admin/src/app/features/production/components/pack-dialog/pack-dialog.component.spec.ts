import { TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { Page } from '../../../../shared/models/page';
import { Product } from '../../../products/models/product';
import { ProductsApiService } from '../../../products/services/products-api.service';
import { OrderApiError, ProductionOrder } from '../../models/order';
import { OrdersApiService } from '../../services/orders-api.service';
import { PackDialogComponent } from './pack-dialog.component';

const order = {
  id: 'order-1', status: 'ready_to_pack', resultProduct: { id: 'p-res', name: 'Cuñapé a granel', unit: { id: 'u-1', abbreviation: 'u' } },
  lot: { id: 'lot-1', code: 'L-1' },
  packing: { unitsPerPack: 6, bagsPerPack: 1, bulkAvailable: '82.0000', bulkUnitAbbreviation: 'u', packings: [] },
} as unknown as ProductionOrder;

function product(id: string, name: string, tracksStock: boolean): Product {
  return { id, name, tracksStock } as Product;
}

describe('PackDialogComponent', () => {
  let api: jasmine.SpyObj<OrdersApiService>;
  let modal: jasmine.SpyObj<NgbActiveModal>;

  function setup() {
    api = jasmine.createSpyObj<OrdersApiService>('api', ['pack']);
    modal = jasmine.createSpyObj<NgbActiveModal>('modal', ['close', 'dismiss']);
    const products = jasmine.createSpyObj<ProductsApiService>('products', ['list']);
    const results = [product('p-res', 'Cuñapé a granel', true), product('p-pack', 'Pack x6', true),
      product('p-bag', 'Bolsa', true), product('p-svc', 'Servicio', false)];
    products.list.and.returnValue(of({ count: 4, next: null, previous: null, results } as Page<Product>));
    TestBed.configureTestingModule({ imports: [PackDialogComponent], providers: [...provideTestTranslations(),
      { provide: OrdersApiService, useValue: api }, { provide: ProductsApiService, useValue: products },
      { provide: NgbActiveModal, useValue: modal }] });
    const fixture = TestBed.createComponent(PackDialogComponent);
    fixture.componentInstance.order = order;
    fixture.detectChanges();
    return fixture;
  }

  it('offers only stock-tracked products other than the bulk one', () => {  // INV-03, UI-02
    const component = setup().componentInstance;
    expect(component.options.map(option => option.id)).toEqual(['p-pack', 'p-bag']);
  });

  it('summarises the conversion and does not submit an invalid form', () => {  // INV-02, UI-02, AC-07
    const fixture = setup();
    fixture.componentInstance.form.patchValue({ packs: 6 });
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).querySelector('[data-testid="summary"]')?.textContent).toContain('36');
    fixture.componentInstance.submit();
    expect(api.pack).not.toHaveBeenCalled();
    fixture.componentInstance.form.patchValue({ packProductId: 'p-pack', bagProductId: 'p-bag', packs: 0 });
    fixture.componentInstance.submit();
    expect(api.pack).not.toHaveBeenCalled();
  });

  it('sends the same request id on every attempt and closes with the updated order', () => {  // AC-03, AC-01
    const fixture = setup();
    const component = fixture.componentInstance;
    api.pack.and.returnValue(of(order));
    component.form.setValue({ packProductId: 'p-pack', bagProductId: 'p-bag', packs: 6 });
    component.submit();
    expect(api.pack).toHaveBeenCalledOnceWith('order-1',
      { requestId: component.requestId, packs: 6, packProductId: 'p-pack', bagProductId: 'p-bag' });
    expect(modal.close).toHaveBeenCalledWith(order);
  });

  it('lists every shortage and keeps the dialog open', () => {  // AC-02, UI-02
    const fixture = setup();
    const component = fixture.componentInstance;
    api.pack.and.returnValue(throwError(() => new OrderApiError('x', 409, { code: 'insufficient_stock' }, false,
      [{ productId: 'p-bag', productName: 'Bolsa', unitAbbreviation: 'u', requested: '20.0000', available: '2.0000', missing: '18.0000' }])));
    component.form.setValue({ packProductId: 'p-pack', bagProductId: 'p-bag', packs: 20 });
    component.submit();
    fixture.detectChanges();
    expect(modal.close).not.toHaveBeenCalled();
    expect((fixture.nativeElement as HTMLElement).querySelector('[data-testid="shortages"]')?.textContent).toContain('Bolsa');
  });
});
