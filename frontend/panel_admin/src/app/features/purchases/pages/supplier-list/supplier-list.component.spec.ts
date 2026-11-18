import { provideTestTranslations } from '../../../../core/i18n/testing';
import { signal } from '@angular/core';
import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { provideRouter } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';

import { CompactViewportService } from '../../../../core/layout/compact-viewport.service';
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

  const compactState = signal(false);

  function create(compact: boolean): void {
    compactState.set(compact);
    fixture = TestBed.createComponent(SupplierListComponent);
    component = fixture.componentInstance;
  }

  beforeEach(async () => {
    api = jasmine.createSpyObj<SuppliersApiService>('SuppliersApiService', ['list', 'activate', 'deactivate']);
    api.list.and.returnValue(of(page([active, inactive])));
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);

    await TestBed.configureTestingModule({
      imports: [SupplierListComponent],
      providers: [...provideTestTranslations(), 
        provideRouter([]),
        { provide: SuppliersApiService, useValue: api },
        { provide: ToastrService, useValue: toastr },
        { provide: CompactViewportService, useValue: { compact: compactState.asReadonly() } },
      ],
    }).compileComponents();

    create(false);
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

  describe('en pantalla estrecha', () => {
    const q = (css: string): HTMLElement | null => (fixture.nativeElement as HTMLElement).querySelector(css);

    beforeEach(() => {
      create(true);
      fixture.detectChanges();
      fixture.detectChanges();
    });

    it('muestra tarjetas en lugar de la tabla, con identificación, teléfono, correo y estado', () => {
      expect(q('ngx-datatable')).toBeNull();
      const cards = fixture.nativeElement.querySelectorAll('[data-testid="supplier-card"]');
      expect(cards.length).toBe(2);
      const first = (cards[0] as HTMLElement).textContent ?? '';
      for (const expected of ['Distribuidora Sur', 'NIT-1020', '76543210', 'ventas@sur.com', 'Activo']) {
        expect(first).toContain(expected);
      }
      expect((cards[1] as HTMLElement).textContent).toContain('—');
    });

    it('cada tarjeta tiene ver, editar, compras y activar/desactivar con nombre accesible', () => {
      const card = q('[data-testid="supplier-card"]') as HTMLElement;
      expect(card.querySelector('[data-testid="card-view"]')?.getAttribute('href')).toBe('/pocketbiz/purchases/suppliers/a');
      expect(card.querySelector('[data-testid="card-edit"]')?.getAttribute('href')).toBe('/pocketbiz/purchases/suppliers/a/edit');
      expect(card.querySelector('[data-testid="card-purchases"]')?.getAttribute('href')).toBe('/pocketbiz/purchases?supplierId=a');
      expect(card.querySelector('[data-testid="card-toggle"]')?.getAttribute('aria-label')).toContain('Distribuidora Sur');
    });

    it('el botón de agregar está arriba de los filtros', () => {
      const add = q('[data-testid="add-supplier"]') as HTMLElement;
      const toolbar = q('[data-testid="filters-toolbar"]') as HTMLElement;
      expect(add.getAttribute('href')).toBe('/pocketbiz/purchases/suppliers/new');
      expect(add.compareDocumentPosition(toolbar) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    });

    it('los filtros están colapsados y se abren y cierran con el botón «Filtros»', () => {
      const panel = q('[data-testid="filters"]') as HTMLElement;
      const toggle = q('[data-testid="filters-toggle"]') as HTMLButtonElement;
      expect(panel.classList).toContain('d-none');
      expect(toggle.getAttribute('aria-expanded')).toBe('false');
      toggle.click();
      fixture.detectChanges();
      expect(panel.classList).not.toContain('d-none');
      expect(toggle.getAttribute('aria-expanded')).toBe('true');
    });

    it('no pide datos al escribir; «Aplicar» pide, cierra el panel y muestra el filtro como chip', fakeAsync(() => {
      component.filtersOpen = true;
      component.searchControl.setValue(' sur ');
      component.statusControl.setValue('all');
      tick(400);
      expect(api.list).toHaveBeenCalledTimes(1);

      (q('[data-testid="apply-filters"]') as HTMLButtonElement).click();
      fixture.detectChanges();
      tick();

      expect(api.list).toHaveBeenCalledTimes(2);
      expect(lastListParams()).toEqual({ search: 'sur', active: undefined, page: 1, pageSize: 10 });
      expect(component.filtersOpen).toBeFalse();
      expect(q('[data-testid="filters-count"]')?.textContent?.trim()).toBe('2');
      expect(q('[data-testid="filters-chips"]')?.textContent).toContain('sur');
    }));

    it('«Limpiar filtros» vuelve a los activos sin búsqueda', () => {
      component.searchControl.setValue('x', { emitEvent: false });
      component.statusControl.setValue('inactive', { emitEvent: false });
      component.clearFilters();
      expect(lastListParams()).toEqual({ search: '', active: true, page: 1, pageSize: 10 });
      expect(component.filtersActive).toBeFalse();
    });

    it('pagina con ngb-pagination cuando hay más de una página', () => {
      api.list.and.returnValue(of(page([active], 25)));
      component.clearFilters();
      fixture.detectChanges();
      expect(q('ngb-pagination')).not.toBeNull();
      component.onPageNumber(2);
      expect(lastListParams()?.page).toBe(2);
    });
  });
});
