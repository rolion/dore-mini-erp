import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { ToastrService } from 'ngx-toastr';
import { BehaviorSubject, Subject, of, throwError } from 'rxjs';
import { ModulesService } from '../../../../core/service/modules.service';
import { UnitsApiService } from '../../../inventory';

import { Product, ProductApiError } from '../../models/product';
import { ProductsApiService } from '../../services/products-api.service';
import { makeProduct } from '../../testing/product-fixtures';
import { ProductFormComponent } from './product-form.component';

describe('ProductFormComponent', () => {
  let api: jasmine.SpyObj<ProductsApiService>;
  let toastr: jasmine.SpyObj<ToastrService>;
  let router: Router;
  let enabled: BehaviorSubject<ReadonlySet<string> | null>;
  let units: jasmine.SpyObj<UnitsApiService>;
  let navigate: jasmine.Spy;

  beforeEach(() => {
    api = jasmine.createSpyObj<ProductsApiService>('ProductsApiService', ['get', 'create', 'update']);
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    enabled = new BehaviorSubject<ReadonlySet<string> | null>(new Set(['catalog']));
    units = jasmine.createSpyObj<UnitsApiService>('UnitsApiService', ['list']);
    units.list.and.returnValue(
      of({ count: 1, next: null, previous: null, results: [{ id: 'u-1', name: 'Kilogramo', abbreviation: 'kg', allowsFractions: true, active: true, inUse: false }] }),
    );
    TestBed.configureTestingModule({
      providers: [
        provideRouter([
          { path: 'pocketbiz/catalog/products/new', component: ProductFormComponent },
          { path: 'pocketbiz/catalog/products/:id/edit', component: ProductFormComponent },
        ]),
        { provide: ProductsApiService, useValue: api },
        { provide: ToastrService, useValue: toastr },
        { provide: UnitsApiService, useValue: units },
        {
          provide: ModulesService,
          useValue: { enabledKeys$: enabled.asObservable(), get enabledKeysValue() { return enabled.value; } },
        },
      ],
    });
    router = TestBed.inject(Router);
    navigate = spyOn(router, 'navigate').and.resolveTo(true);
  });

  async function open(url: string) {
    const harness = await RouterTestingHarness.create();
    const component = await harness.navigateByUrl(url, ProductFormComponent);
    harness.detectChanges();
    return { harness, component, el: harness.routeNativeElement as HTMLElement };
  }

  function submitButton(el: HTMLElement): HTMLButtonElement {
    return el.querySelector('button[type="submit"]') as HTMLButtonElement;
  }

  describe('create mode', () => {
    it('starts empty, without a state field, with Guardar disabled (AC-12)', async () => {
      const { component, el } = await open('/pocketbiz/catalog/products/new');

      expect(component.isEdit).toBeFalse();
      expect(api.get).not.toHaveBeenCalled();
      expect(component.form.getRawValue()).toEqual({ name: '', description: '', salePrice: '', tracksStock: false, baseUnitId: '' });
      expect(submitButton(el).disabled).toBeTrue();
      expect(el.querySelector('[formControlName="active"]')).toBeNull();
    });

    it('requires a non blank name of at most 150 characters (AC-02, AC-12)', async () => {
      const { component } = await open('/pocketbiz/catalog/products/new');
      const name = component.form.controls.name;

      for (const [value, valid] of [['', false], ['   ', false], ['a', true], ['a'.repeat(150), true], ['a'.repeat(151), false]] as const) {
        name.setValue(value);
        expect(name.valid).withContext(JSON.stringify(value)).toBe(valid);
      }
    });

    it('accepts only prices >= 0 with up to 2 decimals (AC-03, AC-12)', async () => {
      const { component } = await open('/pocketbiz/catalog/products/new');
      const price = component.form.controls.salePrice;

      for (const value of ['0', '0.00', '35', '35.5', '35,50', '9999999999.99']) {
        price.setValue(value);
        expect(price.valid).withContext(value).toBeTrue();
      }
      for (const value of ['', '-1', '35.555', 'abc', '1e3', '10000000000']) {
        price.setValue(value);
        expect(price.valid).withContext(value).toBeFalse();
      }
    });

    it('shows validation messages once the fields are touched (AC-12)', async () => {
      const { harness, component, el } = await open('/pocketbiz/catalog/products/new');
      component.form.controls.name.markAsTouched();
      component.form.controls.salePrice.markAsTouched();
      harness.detectChanges();

      const text = el.textContent ?? '';
      expect(text).toContain('El nombre es obligatorio.');
      expect(text).toContain('El precio de venta es obligatorio.');
    });

    it('creates the product sending trimmed values and a dot decimal, then goes to the list (AC-01, AC-12)', async () => {
      const { harness, component, el } = await open('/pocketbiz/catalog/products/new');
      api.create.and.returnValue(of(makeProduct()));
      component.form.setValue({ name: '  Cuñapé  ', description: ' Tradicional ', salePrice: '35,5', tracksStock: false, baseUnitId: '' });
      harness.detectChanges();
      expect(submitButton(el).disabled).toBeFalse();

      component.onSubmit();

      expect(api.create).toHaveBeenCalledOnceWith({ name: 'Cuñapé', description: 'Tradicional', salePrice: '35.5' });
      expect(toastr.success).toHaveBeenCalledWith('Producto creado');
      expect(navigate).toHaveBeenCalledWith(['/pocketbiz/catalog/products']);
    });

    it('does not call the API when the form is invalid (AC-02, AC-03)', async () => {
      const { component } = await open('/pocketbiz/catalog/products/new');
      component.form.setValue({ name: '', description: '', salePrice: '-1', tracksStock: false, baseUnitId: '' });

      component.onSubmit();

      expect(api.create).not.toHaveBeenCalled();
      expect(component.form.controls.name.touched).toBeTrue();
    });

    it('shows server validation errors under each field and clears them on edit (AC-12)', async () => {
      const { harness, component, el } = await open('/pocketbiz/catalog/products/new');
      component.form.setValue({ name: 'x', description: '', salePrice: '1', tracksStock: false, baseUnitId: '' });
      api.create.and.returnValue(
        throwError(() => new ProductApiError('Revisa los datos ingresados.', 400, {
          name: ['Ya existe.'],
          salePrice: ['Precio fuera de rango.'],
        })),
      );

      component.onSubmit();
      harness.detectChanges();

      const text = el.textContent ?? '';
      expect(text).toContain('Ya existe.');
      expect(text).toContain('Precio fuera de rango.');
      expect(navigate).not.toHaveBeenCalled();
      expect(component.saving).toBeFalse();

      component.form.controls.name.setValue('y');
      harness.detectChanges();
      expect(el.textContent).not.toContain('Ya existe.');
    });

    it('toasts non-validation errors and keeps the typed values (AC-12)', async () => {
      const { component } = await open('/pocketbiz/catalog/products/new');
      component.form.setValue({ name: 'x', description: 'd', salePrice: '1', tracksStock: false, baseUnitId: '' });
      api.create.and.returnValue(throwError(() => new ProductApiError('Sin conexión', 0)));

      component.onSubmit();

      expect(toastr.error).toHaveBeenCalledWith('Sin conexión');
      expect(component.form.getRawValue()).toEqual({ name: 'x', description: 'd', salePrice: '1', tracksStock: false, baseUnitId: '' });
    });

    it('ignores a second submit while saving (AC-12)', async () => {
      const { component } = await open('/pocketbiz/catalog/products/new');
      const pending = new Subject<Product>();
      api.create.and.returnValue(pending);
      component.form.setValue({ name: 'x', description: '', salePrice: '1', tracksStock: false, baseUnitId: '' });

      component.onSubmit();
      component.onSubmit();

      expect(api.create).toHaveBeenCalledTimes(1);
      expect(component.saving).toBeTrue();
    });
  });

  describe('edit mode', () => {
    it('loads the product and fills the form (AC-12)', async () => {
      api.get.and.returnValue(of(makeProduct({ id: 'p-9', name: 'Chipa', description: '', salePrice: '5.50' })));
      const { component } = await open('/pocketbiz/catalog/products/p-9/edit');

      expect(component.isEdit).toBeTrue();
      expect(api.get).toHaveBeenCalledOnceWith('p-9');
      expect(component.form.getRawValue()).toEqual({ name: 'Chipa', description: '', salePrice: '5.50', tracksStock: false, baseUnitId: '' });
    });

    it('updates the product and goes to its detail (AC-04, AC-12)', async () => {
      api.get.and.returnValue(of(makeProduct({ id: 'p-9' })));
      api.update.and.returnValue(of(makeProduct({ id: 'p-9', name: 'Nuevo' })));
      const { component } = await open('/pocketbiz/catalog/products/p-9/edit');
      component.form.controls.name.setValue('Nuevo');

      component.onSubmit();

      expect(api.update).toHaveBeenCalledOnceWith('p-9', {
        name: 'Nuevo',
        description: 'Tradicional',
        salePrice: '35.00',
      });
      expect(toastr.success).toHaveBeenCalledWith('Producto actualizado');
      expect(navigate).toHaveBeenCalledWith(['/pocketbiz/catalog/products', 'p-9']);
    });

    it('warns and goes back to the list when the product does not exist (AC-13)', async () => {
      api.get.and.returnValue(throwError(() => new ProductApiError('Producto no encontrado.', 404)));
      await open('/pocketbiz/catalog/products/zzz/edit');

      expect(toastr.error).toHaveBeenCalledWith('Producto no encontrado.');
      expect(navigate).toHaveBeenCalledWith(['/pocketbiz/catalog/products']);
    });
  });

  describe('inventory section (PB-INV-001)', () => {
    it('is hidden and not sent while Inventario is disabled (AC-05)', async () => {
      api.create.and.returnValue(of(makeProduct()));
      const { component, el } = await open('/pocketbiz/catalog/products/new');
      expect(el.querySelector('#product-tracks-stock')).toBeNull();
      component.form.patchValue({ name: 'x', salePrice: '1' });
      component.onSubmit();
      expect(api.create).toHaveBeenCalledOnceWith({ name: 'x', description: '', salePrice: '1' });
    });

    it('shows «Controlar stock» off by default and asks for a unit when turned on (AC-01, AC-04)', async () => {
      enabled.next(new Set(['catalog', 'inventory']));
      const { component, harness, el } = await open('/pocketbiz/catalog/products/new');
      expect(units.list).toHaveBeenCalled();
      const toggle = el.querySelector('#product-tracks-stock') as HTMLInputElement;
      expect(toggle.checked).toBeFalse();
      expect(el.querySelector('#product-base-unit')).toBeNull();
      component.form.patchValue({ name: 'x', salePrice: '1', tracksStock: true });
      harness.detectChanges();
      expect(el.querySelector('#product-base-unit')).not.toBeNull();
      expect(component.form.invalid).toBeTrue();
      component.form.controls.baseUnitId.setValue('u-1');
      expect(component.form.valid).toBeTrue();
    });

    it('sends the stock fields and clears the unit when stock is off (AC-01)', async () => {
      enabled.next(new Set(['catalog', 'inventory']));
      api.create.and.returnValue(of(makeProduct()));
      const { component } = await open('/pocketbiz/catalog/products/new');
      component.form.patchValue({ name: 'x', salePrice: '1', tracksStock: true, baseUnitId: 'u-1' });
      component.onSubmit();
      expect(api.create.calls.mostRecent().args[0]).toEqual(
        { name: 'x', description: '', salePrice: '1', tracksStock: true, baseUnitId: 'u-1' });
      component.form.controls.tracksStock.setValue(false);
      component.onSubmit();
      expect(api.create.calls.mostRecent().args[0]).toEqual(
        { name: 'x', description: '', salePrice: '1', tracksStock: false, baseUnitId: null });
    });

    it('keeps an inactive current unit selectable when editing (EDGE-03)', async () => {
      enabled.next(new Set(['catalog', 'inventory']));
      api.get.and.returnValue(
        of(makeProduct({ id: 'p-9', tracksStock: true, baseUnit: { id: 'u-old', name: 'Litro', abbreviation: 'l' } })),
      );
      const { component } = await open('/pocketbiz/catalog/products/p-9/edit');
      expect(component.form.controls.baseUnitId.value).toBe('u-old');
      expect(component.unitOptions.map((o) => o.id)).toContain('u-old');
    });

    it('shows the history lock message without losing the data (AC-03)', async () => {
      enabled.next(new Set(['catalog', 'inventory']));
      api.get.and.returnValue(of(makeProduct({ id: 'p-9', tracksStock: true, baseUnit: { id: 'u-1', name: 'Kilogramo', abbreviation: 'kg' } })));
      api.update.and.returnValue(
        throwError(() => new ProductApiError('Este producto tiene movimientos de inventario; usa el procedimiento de regularización.', 409, {}, 'stock_history_locked')),
      );
      const { component, harness, el } = await open('/pocketbiz/catalog/products/p-9/edit');
      component.form.controls.tracksStock.setValue(false);
      component.onSubmit();
      harness.detectChanges();
      expect(el.querySelector('.alert-warning')?.textContent).toContain('regularización');
      expect(component.form.controls.name.value).toBe('Cuñapé grande');
      expect(toastr.error).not.toHaveBeenCalled();
    });
  });
});
