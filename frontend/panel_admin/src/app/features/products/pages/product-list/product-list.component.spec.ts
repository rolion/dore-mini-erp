import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { provideRouter } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';

import { Product, ProductApiError } from '../../models/product';
import { Page } from '../../../../shared/models/page';
import { ProductsApiService } from '../../services/products-api.service';
import { makeProduct } from '../../testing/product-fixtures';
import { ProductListComponent } from './product-list.component';

interface ToggleHook {
  confirmToggle(product: Product): Promise<boolean>;
}

function page(results: Product[], count = results.length): Page<Product> {
  return { count, next: null, previous: null, results };
}

describe('ProductListComponent', () => {
  let fixture: ComponentFixture<ProductListComponent>;
  let component: ProductListComponent;
  let api: jasmine.SpyObj<ProductsApiService>;
  let toastr: jasmine.SpyObj<ToastrService>;

  const active = makeProduct({ id: 'a', name: 'Cuñapé grande' });
  const inactive = makeProduct({ id: 'b', name: 'Chipa', active: false, salePrice: '5.50' });

  beforeEach(async () => {
    api = jasmine.createSpyObj<ProductsApiService>('ProductsApiService', ['list', 'activate', 'deactivate']);
    api.list.and.returnValue(of(page([active, inactive])));
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);

    await TestBed.configureTestingModule({
      imports: [ProductListComponent],
      providers: [
        provideRouter([]),
        { provide: ProductsApiService, useValue: api },
        { provide: ToastrService, useValue: toastr },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ProductListComponent);
    component = fixture.componentInstance;
  });

  function lastListParams() {
    return api.list.calls.mostRecent().args[0];
  }

  it('loads the first page with 10 rows, no filters, and shows the products (AC-10)', () => {
    fixture.detectChanges();

    expect(api.list).toHaveBeenCalledOnceWith({ search: '', active: undefined, page: 1, pageSize: 10 });
    expect(component.rows).toEqual([active, inactive]);
    expect(component.total).toBe(2);
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Cuñapé grande');
    expect(text).toContain('5.50');
    expect(text).toContain('Activo');
    expect(text).toContain('Inactivo');
  });

  it('links the "+" button to the new product form (AC-10)', () => {
    fixture.detectChanges();
    const link = fixture.debugElement.query(By.css('a[title="Nuevo producto"]'));
    expect((link.nativeElement as HTMLAnchorElement).getAttribute('href')).toBe('/catalog/products/new');
  });

  it('searches by name with debounce and goes back to the first page (AC-06, AC-10)', fakeAsync(() => {
    fixture.detectChanges();
    component.onPage({ offset: 2 });
    expect(lastListParams()?.page).toBe(3);

    component.searchControl.setValue('  cu ');
    tick(299);
    expect(api.list).toHaveBeenCalledTimes(2);
    tick(1);

    expect(api.list).toHaveBeenCalledTimes(3);
    expect(lastListParams()).toEqual({ search: 'cu', active: undefined, page: 1, pageSize: 10 });
  }));

  it('filters by state Activos / Inactivos / Todos (AC-10)', () => {
    fixture.detectChanges();

    component.statusControl.setValue('inactive');
    expect(lastListParams()?.active).toBe(false);
    component.statusControl.setValue('active');
    expect(lastListParams()?.active).toBe(true);
    component.statusControl.setValue('all');
    expect(lastListParams()?.active).toBeUndefined();
  });

  it('does not reload when the table re-emits the current page (AC-10)', () => {
    fixture.detectChanges();
    component.onPage({ offset: 0 });
    expect(api.list).toHaveBeenCalledTimes(1);
  });

  it('requests the page selected in the table (AC-10)', () => {
    api.list.and.returnValue(of(page([active], 25)));
    fixture.detectChanges();
    expect(component.total).toBe(25);

    component.onPage({ offset: 1 });
    expect(lastListParams()?.page).toBe(2);
    expect(component.pageIndex).toBe(1);
  });

  it('shows the empty state when there are no products (EDGE-06)', () => {
    api.list.and.returnValue(of(page([])));
    fixture.detectChanges();
    fixture.detectChanges();
    expect(component.rows).toEqual([]);
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('No hay productos');
  });

  it('informs the error and keeps working when the list fails (AC-10)', () => {
    api.list.and.returnValue(throwError(() => new ProductApiError('Sin conexión', 0)));
    fixture.detectChanges();

    expect(toastr.error).toHaveBeenCalledWith('Sin conexión');
    expect(component.rows).toEqual([]);
    expect(component.loading).toBeFalse();

    api.list.and.returnValue(of(page([active])));
    component.onPage({ offset: 1 });
    expect(component.rows).toEqual([active]);
  });

  it('deactivates an active product after confirmation and reloads (AC-11)', async () => {
    fixture.detectChanges();
    const hook = component as unknown as ToggleHook;
    const confirm = spyOn(hook, 'confirmToggle').and.resolveTo(true);
    api.deactivate.and.returnValue(of({ ...active, active: false }));

    await component.toggleActive(active);

    expect(confirm).toHaveBeenCalledWith(active);
    expect(api.deactivate).toHaveBeenCalledOnceWith('a');
    expect(toastr.success).toHaveBeenCalledWith('Producto desactivado');
    expect(api.list).toHaveBeenCalledTimes(2);
  });

  it('activates an inactive product after confirmation (AC-11)', async () => {
    fixture.detectChanges();
    spyOn(component as unknown as ToggleHook, 'confirmToggle').and.resolveTo(true);
    api.activate.and.returnValue(of({ ...inactive, active: true }));

    await component.toggleActive(inactive);

    expect(api.activate).toHaveBeenCalledOnceWith('b');
    expect(toastr.success).toHaveBeenCalledWith('Producto activado');
  });

  it('does nothing when the confirmation is cancelled (AC-11)', async () => {
    fixture.detectChanges();
    spyOn(component as unknown as ToggleHook, 'confirmToggle').and.resolveTo(false);

    await component.toggleActive(active);

    expect(api.deactivate).not.toHaveBeenCalled();
    expect(api.activate).not.toHaveBeenCalled();
    expect(api.list).toHaveBeenCalledTimes(1);
  });

  it('shows the server error if the state change fails (AC-11)', async () => {
    fixture.detectChanges();
    spyOn(component as unknown as ToggleHook, 'confirmToggle').and.resolveTo(true);
    api.deactivate.and.returnValue(throwError(() => new ProductApiError('Producto no encontrado.', 404)));

    await component.toggleActive(active);

    expect(toastr.error).toHaveBeenCalledWith('Producto no encontrado.');
    expect(toastr.success).not.toHaveBeenCalled();
  });
});
