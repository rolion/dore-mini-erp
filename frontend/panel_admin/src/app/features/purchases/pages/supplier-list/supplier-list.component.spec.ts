import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { provideRouter } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';

import { Page } from '../../../../shared/models/page';
import { Supplier, SupplierApiError } from '../../models/supplier';
import { SuppliersApiService } from '../../services/suppliers-api.service';
import { makeSupplier } from '../../testing/supplier-fixtures';
import { SupplierListComponent } from './supplier-list.component';

interface ToggleHook {
  confirmToggle(supplier: Supplier): Promise<boolean>;
}

function page(results: Supplier[], count = results.length): Page<Supplier> {
  return { count, next: null, previous: null, results };
}

describe('SupplierListComponent', () => {
  let fixture: ComponentFixture<SupplierListComponent>;
  let component: SupplierListComponent;
  let api: jasmine.SpyObj<SuppliersApiService>;
  let toastr: jasmine.SpyObj<ToastrService>;

  const active = makeSupplier({ id: 'a', name: 'Distribuidora Sur' });
  const inactive = makeSupplier({ id: 'b', name: 'Norte', taxId: '', phone: '', email: '', active: false });

  beforeEach(async () => {
    api = jasmine.createSpyObj<SuppliersApiService>('SuppliersApiService', ['list', 'activate', 'deactivate']);
    api.list.and.returnValue(of(page([active, inactive])));
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);

    await TestBed.configureTestingModule({
      imports: [SupplierListComponent],
      providers: [
        provideRouter([]),
        { provide: SuppliersApiService, useValue: api },
        { provide: ToastrService, useValue: toastr },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(SupplierListComponent);
    component = fixture.componentInstance;
  });

  function lastListParams() {
    return api.list.calls.mostRecent().args[0];
  }

  it('loads only active suppliers by default, 10 per page (AC-10)', () => {
    fixture.detectChanges();
    expect(api.list).toHaveBeenCalledOnceWith({ search: '', active: true, page: 1, pageSize: 10 });
    expect(component.statusControl.value).toBe('active');
  });

  it('shows name, tax id, phone, email and state, with dashes for empty data (AC-10)', () => {
    fixture.detectChanges();
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    for (const expected of ['Distribuidora Sur', 'NIT-1020', '76543210', 'ventas@sur.com', 'Activo', 'Inactivo', '—']) {
      expect(text).toContain(expected);
    }
    expect(component.total).toBe(2);
  });

  it('offers Activos, Inactivos and Todos, Activos first (AC-10)', () => {
    fixture.detectChanges();
    const options = fixture.debugElement
      .queryAll(By.css('select option'))
      .map((o) => (o.nativeElement as HTMLOptionElement).textContent?.trim());
    expect(options).toEqual(['Activos', 'Inactivos', 'Todos']);
  });

  it('links to the new supplier form and to the purchases list filtered by supplier (AC-10)', () => {
    fixture.detectChanges();
    fixture.detectChanges();
    const add = fixture.debugElement.query(By.css('a[title="Nuevo proveedor"]'));
    expect((add.nativeElement as HTMLAnchorElement).getAttribute('href')).toBe('/pocketbiz/purchases/suppliers/new');
    const purchases = fixture.debugElement.query(By.css('a[title="Ver compras"]'));
    expect((purchases.nativeElement as HTMLAnchorElement).getAttribute('href')).toBe(
      '/pocketbiz/purchases?supplierId=a',
    );
  });

  it('searches by name or tax id with a debounced field and goes back to page 1 (AC-10)', fakeAsync(() => {
    fixture.detectChanges();
    component.onPage({ offset: 2 });
    expect(lastListParams()?.page).toBe(3);

    component.searchControl.setValue('  nit ');
    tick(299);
    expect(api.list).toHaveBeenCalledTimes(2);
    tick(1);

    expect(api.list).toHaveBeenCalledTimes(3);
    expect(lastListParams()).toEqual({ search: 'nit', active: true, page: 1, pageSize: 10 });
  }));

  it('maps the state filter to the active parameter (AC-10)', () => {
    fixture.detectChanges();
    component.statusControl.setValue('inactive');
    expect(lastListParams()?.active).toBeFalse();
    component.statusControl.setValue('all');
    expect(lastListParams()?.active).toBeUndefined();
    component.statusControl.setValue('active');
    expect(lastListParams()?.active).toBeTrue();
  });

  it('shows the empty state message (AC-10)', () => {
    api.list.and.returnValue(of(page([])));
    fixture.detectChanges();
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('No hay proveedores que coincidan');
  });

  it('shows a toast when loading fails (AC-10)', () => {
    api.list.and.returnValue(throwError(() => new SupplierApiError('Sin conexión', 0)));
    fixture.detectChanges();
    expect(toastr.error).toHaveBeenCalledWith('Sin conexión');
    expect(component.loading).toBeFalse();
  });

  it('deactivates after confirmation, notifies and reloads (AC-10)', async () => {
    api.deactivate.and.returnValue(of({ ...active, active: false }));
    fixture.detectChanges();
    spyOn(component as unknown as ToggleHook, 'confirmToggle').and.resolveTo(true);

    await component.toggleActive(active);

    expect(api.deactivate).toHaveBeenCalledWith('a');
    expect(toastr.success).toHaveBeenCalledWith('Proveedor desactivado');
    expect(api.list).toHaveBeenCalledTimes(2);
  });

  it('activates an inactive supplier after confirmation (AC-10)', async () => {
    api.activate.and.returnValue(of({ ...inactive, active: true }));
    fixture.detectChanges();
    spyOn(component as unknown as ToggleHook, 'confirmToggle').and.resolveTo(true);

    await component.toggleActive(inactive);

    expect(api.activate).toHaveBeenCalledWith('b');
    expect(toastr.success).toHaveBeenCalledWith('Proveedor activado');
  });

  it('does nothing when the confirmation is cancelled (AC-10)', async () => {
    fixture.detectChanges();
    spyOn(component as unknown as ToggleHook, 'confirmToggle').and.resolveTo(false);

    await component.toggleActive(active);

    expect(api.deactivate).not.toHaveBeenCalled();
    expect(api.list).toHaveBeenCalledTimes(1);
  });

  it('shows an error toast when the state change fails (AC-10)', async () => {
    api.deactivate.and.returnValue(throwError(() => new SupplierApiError('Proveedor no encontrado.', 404)));
    fixture.detectChanges();
    spyOn(component as unknown as ToggleHook, 'confirmToggle').and.resolveTo(true);

    await component.toggleActive(active);

    expect(toastr.error).toHaveBeenCalledWith('Proveedor no encontrado.');
  });
});
