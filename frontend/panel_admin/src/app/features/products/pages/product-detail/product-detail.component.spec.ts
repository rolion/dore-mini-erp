import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';

import { Product, ProductApiError } from '../../models/product';
import { ProductsApiService } from '../../services/products-api.service';
import { makeProduct } from '../../testing/product-fixtures';
import { ProductDetailComponent } from './product-detail.component';

interface ToggleHook {
  confirmToggle(product: Product): Promise<boolean>;
}

describe('ProductDetailComponent', () => {
  let api: jasmine.SpyObj<ProductsApiService>;
  let toastr: jasmine.SpyObj<ToastrService>;
  let navigate: jasmine.Spy;

  beforeEach(() => {
    api = jasmine.createSpyObj<ProductsApiService>('ProductsApiService', ['get', 'activate', 'deactivate']);
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    TestBed.configureTestingModule({
      providers: [
        provideRouter([{ path: 'catalog/products/:id', component: ProductDetailComponent }]),
        { provide: ProductsApiService, useValue: api },
        { provide: ToastrService, useValue: toastr },
      ],
    });
    navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
  });

  async function open(id = 'p-1') {
    const harness = await RouterTestingHarness.create();
    const component = await harness.navigateByUrl(`/catalog/products/${id}`, ProductDetailComponent);
    harness.detectChanges();
    return { harness, component, el: harness.routeNativeElement as HTMLElement };
  }

  it('shows all the product data in read-only mode (AC-13)', async () => {
    api.get.and.returnValue(of(makeProduct({ description: 'Tradicional', salePrice: '35.00' })));
    const { el } = await open();

    const text = el.textContent ?? '';
    expect(api.get).toHaveBeenCalledOnceWith('p-1');
    expect(text).toContain('Cuñapé grande');
    expect(text).toContain('Tradicional');
    expect(text).toContain('35.00');
    expect(text).toContain('Activo');
    expect(text).toContain('Creado');
    expect(text).toContain('Última actualización');
    expect(el.querySelector('input, textarea')).toBeNull();
  });

  it('links to edit and back to the list (AC-13)', async () => {
    api.get.and.returnValue(of(makeProduct()));
    const { el } = await open();

    const hrefs = Array.from(el.querySelectorAll('a')).map((a) => a.getAttribute('href'));
    expect(hrefs).toContain('/catalog/products/p-1/edit');
    expect(hrefs).toContain('/catalog/products');
  });

  it('shows a placeholder when there is no description (AC-13)', async () => {
    api.get.and.returnValue(of(makeProduct({ description: '' })));
    const { el } = await open();
    expect(el.textContent).toContain('Sin descripción');
  });

  it('warns and goes back to the list when the product does not exist (AC-13)', async () => {
    api.get.and.returnValue(throwError(() => new ProductApiError('Producto no encontrado.', 404)));
    await open('zzz');

    expect(toastr.error).toHaveBeenCalledWith('Producto no encontrado.');
    expect(navigate).toHaveBeenCalledWith(['/catalog/products']);
  });

  it('deactivates after confirmation and updates the badge and button (AC-11)', async () => {
    api.get.and.returnValue(of(makeProduct()));
    api.deactivate.and.returnValue(of(makeProduct({ active: false })));
    const { harness, component, el } = await open();
    expect(el.textContent).toContain('Desactivar');
    spyOn(component as unknown as ToggleHook, 'confirmToggle').and.resolveTo(true);

    await component.toggleActive();
    harness.detectChanges();

    expect(api.deactivate).toHaveBeenCalledOnceWith('p-1');
    expect(toastr.success).toHaveBeenCalledWith('Producto desactivado');
    expect(el.textContent).toContain('Inactivo');
    expect(el.textContent).toContain('Activar');
  });

  it('activates an inactive product after confirmation (AC-11)', async () => {
    api.get.and.returnValue(of(makeProduct({ active: false })));
    api.activate.and.returnValue(of(makeProduct({ active: true })));
    const { component } = await open();
    spyOn(component as unknown as ToggleHook, 'confirmToggle').and.resolveTo(true);

    await component.toggleActive();

    expect(api.activate).toHaveBeenCalledOnceWith('p-1');
    expect(component.product?.active).toBeTrue();
  });

  it('does not change anything when the confirmation is cancelled (AC-11)', async () => {
    api.get.and.returnValue(of(makeProduct()));
    const { component } = await open();
    spyOn(component as unknown as ToggleHook, 'confirmToggle').and.resolveTo(false);

    await component.toggleActive();

    expect(api.deactivate).not.toHaveBeenCalled();
    expect(component.product?.active).toBeTrue();
  });
});
