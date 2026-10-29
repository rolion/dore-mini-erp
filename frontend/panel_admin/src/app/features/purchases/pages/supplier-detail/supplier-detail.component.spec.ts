import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';

import { Supplier, SupplierApiError } from '../../models/supplier';
import { SuppliersApiService } from '../../services/suppliers-api.service';
import { makeSupplier } from '../../testing/supplier-fixtures';
import { SupplierDetailComponent } from './supplier-detail.component';

interface ToggleHook {
  confirmToggle(supplier: Supplier): Promise<boolean>;
}

describe('SupplierDetailComponent', () => {
  let fixture: ComponentFixture<SupplierDetailComponent>;
  let component: SupplierDetailComponent;
  let api: jasmine.SpyObj<SuppliersApiService>;
  let toastr: jasmine.SpyObj<ToastrService>;
  let router: Router;

  async function setup(supplier: Supplier | null): Promise<void> {
    api = jasmine.createSpyObj<SuppliersApiService>('SuppliersApiService', ['get', 'activate', 'deactivate']);
    api.get.and.returnValue(
      supplier ? of(supplier) : throwError(() => new SupplierApiError('Proveedor no encontrado.', 404)),
    );
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    await TestBed.configureTestingModule({
      imports: [SupplierDetailComponent],
      providers: [
        provideRouter([]),
        { provide: SuppliersApiService, useValue: api },
        { provide: ToastrService, useValue: toastr },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: 's-1' }) } } },
      ],
    }).compileComponents();
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    fixture = TestBed.createComponent(SupplierDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  it('shows all the supplier data and the active badge (AC-12)', async () => {
    await setup(makeSupplier());
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    for (const expected of ['Distribuidora Sur', 'NIT-1020', '76543210', 'ventas@sur.com', 'Entrega los martes', 'Activo']) {
      expect(text).toContain(expected);
    }
    expect(api.get).toHaveBeenCalledWith('s-1');
  });

  it('still shows an inactive supplier, with fallback text for missing data (AC-12)', async () => {
    await setup(makeSupplier({ active: false, taxId: '', phone: '', email: '', notes: '' }));
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Inactivo');
    expect(text).toContain('—');
    expect(text).toContain('Sin notas');
    expect(text).toContain('Activar');
  });

  it('offers Editar, Ver compras (filtered by supplier) and Volver (AC-12)', async () => {
    await setup(makeSupplier());
    const hrefs = fixture.debugElement
      .queryAll(By.css('div.m-4 a'))
      .map((a) => (a.nativeElement as HTMLAnchorElement).getAttribute('href'));
    expect(hrefs).toEqual([
      '/pocketbiz/purchases/suppliers/s-1/edit',
      '/pocketbiz/purchases?supplierId=s-1',
      '/pocketbiz/purchases/suppliers',
    ]);
  });

  it('deactivates after confirmation and shows the new state (AC-12)', async () => {
    await setup(makeSupplier());
    api.deactivate.and.returnValue(of(makeSupplier({ active: false })));
    spyOn(component as unknown as ToggleHook, 'confirmToggle').and.resolveTo(true);

    await component.toggleActive();

    expect(api.deactivate).toHaveBeenCalledWith('s-1');
    expect(component.supplier?.active).toBeFalse();
    expect(toastr.success).toHaveBeenCalledWith('Proveedor desactivado');
  });

  it('activates an inactive supplier (AC-12)', async () => {
    await setup(makeSupplier({ active: false }));
    api.activate.and.returnValue(of(makeSupplier()));
    spyOn(component as unknown as ToggleHook, 'confirmToggle').and.resolveTo(true);

    await component.toggleActive();

    expect(api.activate).toHaveBeenCalledWith('s-1');
    expect(toastr.success).toHaveBeenCalledWith('Proveedor activado');
  });

  it('does not change the state when the confirmation is cancelled (AC-12)', async () => {
    await setup(makeSupplier());
    spyOn(component as unknown as ToggleHook, 'confirmToggle').and.resolveTo(false);

    await component.toggleActive();

    expect(api.deactivate).not.toHaveBeenCalled();
    expect(component.supplier?.active).toBeTrue();
  });

  it('returns to the list with a toast when the supplier does not exist (AC-12)', async () => {
    await setup(null);
    expect(toastr.error).toHaveBeenCalledWith('Proveedor no encontrado.');
    expect(router.navigate).toHaveBeenCalledWith(['/pocketbiz/purchases/suppliers']);
  });
});
