import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';

import { Page } from '../../../../shared/models/page';
import { ProductsApiService } from '../../../products';
import { makeProduct } from '../../../products/testing/product-fixtures';
import { PurchaseApiError, PurchaseFieldErrors } from '../../models/purchase';
import { PurchasesApiService } from '../../services/purchases-api.service';
import { SupplierQuickCreateService } from '../../services/supplier-quick-create.service';
import { SuppliersApiService } from '../../services/suppliers-api.service';
import { makePurchase } from '../../testing/purchase-fixtures';
import { makeSupplier } from '../../testing/supplier-fixtures';
import { LineProduct, PurchaseFormComponent } from './purchase-form.component';

const page = <T>(results: T[]): Page<T> => ({ count: results.length, next: null, previous: null, results });
const FLOUR: LineProduct = { id: 'p-1', name: 'Harina', unit: 'kg', allowsFractions: true };
const BOXES: LineProduct = { id: 'p-2', name: 'Cajas', unit: 'u', allowsFractions: false };

describe('PurchaseFormComponent', () => {
  let fixture: ComponentFixture<PurchaseFormComponent>;
  let component: PurchaseFormComponent;
  let purchases: jasmine.SpyObj<PurchasesApiService>;
  let suppliers: jasmine.SpyObj<SuppliersApiService>;
  let products: jasmine.SpyObj<ProductsApiService>;
  let quickCreate: jasmine.SpyObj<SupplierQuickCreateService>;
  let toastr: jasmine.SpyObj<ToastrService>;
  let router: Router;

  async function setup(id: string | null, supplierList = [makeSupplier()]): Promise<void> {
    purchases = jasmine.createSpyObj<PurchasesApiService>('PurchasesApiService', ['get', 'create', 'update']);
    suppliers = jasmine.createSpyObj<SuppliersApiService>('SuppliersApiService', ['list']);
    products = jasmine.createSpyObj<ProductsApiService>('ProductsApiService', ['list']);
    quickCreate = jasmine.createSpyObj<SupplierQuickCreateService>('SupplierQuickCreateService', ['open']);
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    suppliers.list.and.returnValue(of(page(supplierList)));
    products.list.and.returnValue(
      of(
        page([
          makeProduct({ id: 'p-1', name: 'Harina', baseUnit: { id: 'u1', name: 'Kilo', abbreviation: 'kg', allowsFractions: true } }),
          makeProduct({ id: 'p-2', name: 'Cajas', baseUnit: { id: 'u2', name: 'Unidad', abbreviation: 'u', allowsFractions: false } }),
          makeProduct({ id: 'p-3', name: 'Bolsa', baseUnit: null }),
        ]),
      ),
    );
    await TestBed.configureTestingModule({
      imports: [PurchaseFormComponent],
      providers: [
        provideRouter([]),
        { provide: PurchasesApiService, useValue: purchases },
        { provide: SuppliersApiService, useValue: suppliers },
        { provide: ProductsApiService, useValue: products },
        { provide: SupplierQuickCreateService, useValue: quickCreate },
        { provide: ToastrService, useValue: toastr },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap(id ? { id } : {}) } } },
      ],
    }).compileComponents();
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    fixture = TestBed.createComponent(PurchaseFormComponent);
    component = fixture.componentInstance;
  }

  const text = (): string => (fixture.nativeElement as HTMLElement).textContent ?? '';
  const q = <T extends HTMLElement>(selector: string): T | null => fixture.debugElement.query(By.css(selector))?.nativeElement ?? null;

  function validDraft(): void {
    component.form.controls.supplier.setValue({ id: 's-1', name: 'Distribuidora Sur' });
    component.addLine(FLOUR, '2.5', '10.00');
  }

  describe('create', () => {
    beforeEach(async () => {
      await setup(null);
      fixture.detectChanges();
    });

    it('offers only active suppliers and active products enabled for purchase, and starts with today (AC-14, AC-15, AC-19)', () => {
      expect(suppliers.list).toHaveBeenCalledWith(jasmine.objectContaining({ active: true }));
      expect(products.list).toHaveBeenCalledWith(jasmine.objectContaining({ active: true, canBuy: true }));
      expect(component.form.controls.purchaseDate.value).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(component.supplierOptions.map((s) => s.name)).toEqual(['Distribuidora Sur']);
    });

    it('has no tax, discount or extra-cost fields and a read-only total in BOB (AC-15)', () => {
      expect(Object.keys(component.form.controls)).toEqual(['supplier', 'purchaseDate', 'externalReference', 'notes', 'items']);
      expect(text().toLowerCase()).not.toContain('descuento:');
      expect(q('[data-testid="total"]')?.tagName).toBe('TD');
      expect(text()).toContain('BOB');
    });

    it('requires a supplier and a date, and the save button reflects validity (AC-14, AC-16)', () => {
      expect(component.form.invalid).toBeTrue();
      validDraft();
      fixture.detectChanges();
      expect(component.form.valid).toBeTrue();
      expect(q<HTMLButtonElement>('[data-testid="save"]')?.disabled).toBeFalse();
      component.form.controls.purchaseDate.setValue('');
      fixture.detectChanges();
      expect(q<HTMLButtonElement>('[data-testid="save"]')?.disabled).toBeTrue();
    });

    it('computes each subtotal and the total from the lines (AC-15)', () => {
      validDraft();
      component.addLine(BOXES, '3', '7');
      fixture.detectChanges();
      const subtotals = fixture.debugElement.queryAll(By.css('[data-testid="line-subtotal"]')).map((e) => (e.nativeElement as HTMLElement).textContent?.trim());
      expect(subtotals).toEqual(['Bs 25.00', 'Bs 21.00']);
      expect(q('[data-testid="total"]')?.textContent?.trim()).toBe('Bs 46.00');
    });

    it('does not count a line with an invalid quantity or price in the subtotal or the total (REV-06)', () => {
      component.addLine(FLOUR, '2', '10');
      component.addLine(BOXES, '1.5', '4.50');
      component.addLine(FLOUR, '1', '-3');
      fixture.detectChanges();
      const subtotals = fixture.debugElement.queryAll(By.css('[data-testid="line-subtotal"]')).map((e) => (e.nativeElement as HTMLElement).textContent?.trim());
      expect(subtotals).toEqual(['Bs 20.00', '—', '—']);
      expect(q('[data-testid="total"]')?.textContent?.trim()).toBe('Bs 20.00');
    });

    it('shows the unit of the product or a dash (AC-15)', () => {
      component.addLine(FLOUR, '1', '1');
      component.addLine({ id: 'p-3', name: 'Bolsa', unit: '', allowsFractions: true }, '1', '1');
      fixture.detectChanges();
      const units = fixture.debugElement.queryAll(By.css('[data-testid="line-unit"]')).map((e) => (e.nativeElement as HTMLElement).textContent?.trim());
      expect(units).toEqual(['kg', '—']);
    });

    it('marks an invalid quantity or price next to its line, not the others (AC-15)', () => {
      component.addLine(FLOUR, '2', '10');
      component.addLine(FLOUR, '0', '-5');
      component.items.controls.forEach((line) => line.markAllAsTouched());
      fixture.detectChanges();
      const rows = fixture.debugElement.queryAll(By.css('[data-testid="line"]'));
      expect(rows[0].query(By.css('[data-testid="line-quantity-error"]'))).toBeNull();
      expect(rows[1].query(By.css('[data-testid="line-quantity-error"]'))).not.toBeNull();
      expect(rows[1].query(By.css('[data-testid="line-price-error"]'))).not.toBeNull();
      expect(component.form.invalid).toBeTrue();
    });

    it('rejects fractions when the unit does not allow them, even after changing product (INV-04)', () => {
      component.addLine(FLOUR, '1.5', '1');
      const line = component.items.at(0);
      expect(line.controls.quantity.valid).toBeTrue();
      line.controls.product.setValue(BOXES);
      component.onProductChange(line);
      expect(line.controls.quantity.valid).toBeFalse();
    });

    it('adds and removes lines (AC-15)', () => {
      component.addLine();
      component.addLine();
      expect(component.items.length).toBe(2);
      component.removeLine(0);
      expect(component.items.length).toBe(1);
      fixture.detectChanges();
      expect(q('[data-testid="no-lines"]')).toBeNull();
      component.removeLine(0);
      fixture.detectChanges();
      expect(q('[data-testid="no-lines"]')).not.toBeNull();
    });

    it('does not offer in a line the products already chosen in another (AC-15)', () => {
      component.addLine(FLOUR, '1', '1');
      component.addLine();
      expect(component.lineOptions[0].map((p) => p.name)).toEqual(['Harina', 'Cajas', 'Bolsa']);
      expect(component.lineOptions[1].map((p) => p.name)).toEqual(['Cajas', 'Bolsa']);
    });

    it('creates the draft with text amounts and goes to the detail (AC-16)', () => {
      purchases.create.and.returnValue(of(makePurchase({ id: 'new' })));
      validDraft();
      component.form.patchValue({ externalReference: ' F-1 ', notes: ' n ' });
      component.onSubmit();
      expect(purchases.create).toHaveBeenCalledWith({
        supplierId: 's-1',
        purchaseDate: component.form.controls.purchaseDate.value,
        externalReference: 'F-1',
        notes: 'n',
        items: [{ productId: 'p-1', quantity: '2.5', unitPrice: '10.00' }],
      });
      expect(toastr.success).toHaveBeenCalledWith('Compra guardada');
      expect(router.navigate).toHaveBeenCalledWith(['/pocketbiz/purchases', 'new']);
      expect(component.hasUnsavedChanges()).toBeFalse();
    });

    it('does not submit an invalid form (AC-16)', () => {
      component.onSubmit();
      expect(purchases.create).not.toHaveBeenCalled();
      expect(component.form.touched).toBeTrue();
    });

    it('keeps every entry and shows server errors per field and per line (AC-16)', () => {
      const fieldErrors: PurchaseFieldErrors = {
        header: { supplierId: 'Selecciona un proveedor activo.' },
        items: [{ quantity: 'La unidad no admite fracciones.' }],
      };
      purchases.create.and.returnValue(throwError(() => new PurchaseApiError('Revisa los datos ingresados.', 400, fieldErrors)));
      validDraft();
      component.form.patchValue({ notes: 'Importante' });
      component.onSubmit();
      fixture.detectChanges();
      expect(text()).toContain('Selecciona un proveedor activo.');
      expect(q('[data-testid="line-quantity-error"]')?.textContent).toContain('La unidad no admite fracciones.');
      expect(component.items.at(0).controls.quantity.value).toBe('2.5');
      expect(component.form.controls.notes.value).toBe('Importante');
      expect(component.saving).toBeFalse();
      expect(router.navigate).not.toHaveBeenCalled();
    });

    it('shows a general message for a server or network failure and keeps the entries (AC-16)', () => {
      purchases.create.and.returnValue(throwError(() => new PurchaseApiError('No se pudo conectar con el servidor. Inténtalo de nuevo.', 0)));
      validDraft();
      component.onSubmit();
      fixture.detectChanges();
      expect(q('[data-testid="general-error"]')?.textContent).toContain('No se pudo conectar');
      expect(component.items.length).toBe(1);
    });

    it('warns about unsaved changes only after editing (AC-16)', () => {
      expect(component.hasUnsavedChanges()).toBeFalse();
      component.form.controls.notes.setValue('x');
      component.form.controls.notes.markAsDirty();
      expect(component.hasUnsavedChanges()).toBeTrue();
    });
  });

  describe('without suppliers (AC-14)', () => {
    beforeEach(async () => {
      await setup(null, []);
      fixture.detectChanges();
    });

    it('shows the empty message with access to create one', () => {
      expect(q('[data-testid="no-suppliers"]')?.textContent).toContain('No hay proveedores activos.');
      expect(q('[data-testid="create-supplier"]')).not.toBeNull();
    });

    it('creates a supplier in the dialog, selects it and keeps what was typed', async () => {
      component.form.patchValue({ notes: 'No perder', externalReference: 'F-9' });
      component.addLine(FLOUR, '4', '2.00');
      quickCreate.open.and.resolveTo(makeSupplier({ id: 's-9', name: 'Nuevo' }));
      await component.createSupplier();
      fixture.detectChanges();
      expect(component.form.controls.supplier.value).toEqual({ id: 's-9', name: 'Nuevo' });
      expect(component.noSuppliers).toBeFalse();
      expect(q('[data-testid="no-suppliers"]')).toBeNull();
      expect(component.form.controls.notes.value).toBe('No perder');
      expect(component.form.controls.externalReference.value).toBe('F-9');
      expect(component.items.at(0).controls.quantity.value).toBe('4');
    });

    it('does nothing when the dialog is closed without saving', async () => {
      quickCreate.open.and.resolveTo(null);
      await component.createSupplier();
      expect(component.form.controls.supplier.value).toBeNull();
    });
  });

  describe('edit', () => {
    it('loads the draft and saves with PATCH semantics (AC-18)', async () => {
      await setup('c-1');
      purchases.get.and.returnValue(of(makePurchase()));
      purchases.update.and.returnValue(of(makePurchase()));
      fixture.detectChanges();
      expect(component.isEdit).toBeTrue();
      expect(component.form.controls.supplier.value).toEqual({ id: 's-1', name: 'Distribuidora Sur' });
      expect(component.form.controls.externalReference.value).toBe('F-100');
      expect(component.items.length).toBe(1);
      expect(component.items.at(0).controls.quantity.value).toBe('2.500');
      expect(component.hasUnsavedChanges()).toBeFalse();
      component.items.at(0).controls.quantity.setValue('3');
      component.onSubmit();
      expect(purchases.update).toHaveBeenCalledWith('c-1', jasmine.objectContaining({
        items: [{ productId: 'p-1', quantity: '3', unitPrice: '10.00' }],
      }));
      expect(router.navigate).toHaveBeenCalledWith(['/pocketbiz/purchases', 'c-1']);
    });

    it('redirects to the detail when the purchase is no longer editable (AC-18)', async () => {
      await setup('c-1');
      purchases.get.and.returnValue(of(makePurchase({ editable: false })));
      fixture.detectChanges();
      expect(toastr.error).toHaveBeenCalledWith('La compra ya no admite cambios.');
      expect(router.navigate).toHaveBeenCalledWith(['/pocketbiz/purchases', 'c-1']);
      expect(component.items.length).toBe(0);
    });

    it('goes back to the list when the purchase does not exist (AC-18)', async () => {
      await setup('x');
      purchases.get.and.returnValue(throwError(() => new PurchaseApiError('Compra no encontrada.', 404)));
      fixture.detectChanges();
      expect(toastr.error).toHaveBeenCalledWith('Compra no encontrada.');
      expect(router.navigate).toHaveBeenCalledWith(['/pocketbiz/purchases']);
    });

    it('tells that an inactive supplier must be replaced (EDGE-05)', async () => {
      await setup('c-1');
      purchases.get.and.returnValue(of(makePurchase({ supplier: { id: 's-1', name: 'Viejo', active: false } })));
      fixture.detectChanges();
      expect(q('[data-testid="supplier-inactive"]')?.textContent).toContain('inactivo');
    });
  });
});
