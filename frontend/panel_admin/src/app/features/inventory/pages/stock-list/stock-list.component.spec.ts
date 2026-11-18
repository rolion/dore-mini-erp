import { provideTestTranslations } from '../../../../core/i18n/testing';
import { BreakpointObserver } from '@angular/cdk/layout';
import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { BehaviorSubject, of, throwError } from 'rxjs';
import { InventoryApiError } from '../../models/api-error';
import { StockBalance } from '../../models/stock';
import { StockApiService } from '../../services/stock-api.service';
import { StockFiltersState } from '../../services/stock-filters-state';
import { WarehousesApiService } from '../../services/warehouses-api.service';
import { makeWarehouse } from '../../testing/inventory-fixtures';
import { StockListComponent } from './stock-list.component';

const ROW: StockBalance = {
  productId: 'p-1',
  productName: 'Harina',
  productActive: true,
  warehouseId: 'w-1',
  warehouseName: 'Almacén principal',
  warehouseActive: true,
  category: 'packaging',
  canBuy: true,
  canSell: false,
  quantity: '10.000',
  balanceState: 'positive',
  unit: { abbreviation: 'u', allowsFractions: false },
};

describe('StockListComponent', () => {
  let stockApi: jasmine.SpyObj<StockApiService>;
  let fixture: ComponentFixture<StockListComponent>;
  let router: Router;
  let compact$: BehaviorSubject<{ matches: boolean }>;

  async function setup(
    query: Record<string, string> = {},
    rows: StockBalance[] = [ROW],
    seed?: (state: StockFiltersState) => void,
    compact = false,
  ): Promise<void> {
    compact$ = new BehaviorSubject({ matches: compact });
    stockApi = jasmine.createSpyObj<StockApiService>('StockApiService', ['list']);
    stockApi.list.and.returnValue(of({ count: rows.length, next: null, previous: null, results: rows }));
    const warehouses = jasmine.createSpyObj<WarehousesApiService>('WarehousesApiService', ['list']);
    warehouses.list.and.returnValue(
      of({ count: 2, next: null, previous: null, results: [makeWarehouse(), makeWarehouse({ id: 'w-2', name: 'Tienda', isDefault: false })] }),
    );
    await TestBed.configureTestingModule({
      imports: [StockListComponent],
      providers: [...provideTestTranslations(), 
        provideRouter([]),
        { provide: BreakpointObserver, useValue: { observe: () => compact$ } },
        { provide: StockApiService, useValue: stockApi },
        { provide: WarehousesApiService, useValue: warehouses },
        { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: convertToParamMap(query) } } },
      ],
    }).compileComponents();
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    seed?.(TestBed.inject(StockFiltersState));
    fixture = TestBed.createComponent(StockListComponent);
    fixture.detectChanges();
  }

  const el = () => fixture.nativeElement as HTMLElement;

  it('lists balances with quantity and unit and offers «Registrar apertura» (AC-05)', async () => {
    await setup();
    expect(el().querySelector('tbody tr')?.textContent).toContain('Harina');
    expect(el().querySelector('tbody tr')?.textContent).toContain('10');
    expect(el().querySelector('tbody tr')?.textContent).toContain('u');
    const link = el().querySelector('[data-testid="register-opening"]') as HTMLAnchorElement;
    expect(link.textContent).toContain('Registrar apertura');
    expect(link.getAttribute('href')).toBe('/pocketbiz/inventory/stock/opening');
  });

  it('keeps the warehouse sent in the query (after an opening) as the filter (AC-05)', async () => {
    await setup({ warehouse_id: 'w-2' });
    expect(stockApi.list.calls.mostRecent().args[0]?.warehouseId).toBe('w-2');
  });

  it('shows only the allowed columns, without available, reserved or valuation (AC-01, AC-03)', async () => {
    await setup();
    const headers = Array.from(el().querySelectorAll('thead th')).map((th) => th.textContent?.trim());
    expect(headers).toEqual(['Producto', 'Almacén', 'Clasificación', 'Usos', 'Unidad base', 'Existencia', 'Acciones']);
  });

  it('asks the server for active products by default and sends every filter (AC-02)', fakeAsync(() => {
    void setup();
    tick();
    expect(stockApi.list.calls.mostRecent().args[0]).toEqual(jasmine.objectContaining({ active: 'true' }));
    fixture.componentInstance.filterForm.patchValue({ search: ' har ', active: 'all', balance: 'zero' });
    tick(300);
    expect(stockApi.list.calls.mostRecent().args[0]).toEqual(
      jasmine.objectContaining({ search: 'har', active: 'all', balance: 'zero', page: 1 }),
    );
    fixture.componentInstance.clearFilters();
    tick(300);
    expect(stockApi.list.calls.mostRecent().args[0]).toEqual(
      jasmine.objectContaining({ search: undefined, active: 'true', balance: undefined }),
    );
  }));

  it('shows classification and use badges, «Sin clasificar» and «Sin usos» (UI-01, EDGE-01, EDGE-02)', async () => {
    await setup({}, [ROW, { ...ROW, productId: 'p-2', category: null, canBuy: false, canSell: false }]);
    const rows = el().querySelectorAll('tbody tr');
    expect(rows[0].querySelector('[data-testid="category"]')?.textContent).toContain('Empaque');
    expect(rows[0].querySelector('[data-testid="uses"]')?.textContent).toContain('Comprable');
    expect(rows[0].querySelector('[data-testid="uses"]')?.textContent).not.toContain('Vendible');
    expect(rows[1].querySelector('[data-testid="category"]')?.textContent).toContain('Sin clasificar');
    expect(rows[1].querySelector('[data-testid="uses"]')?.textContent).toContain('Sin usos');
  });

  it('sends the classification and use filters combined and clears them all (AC-02)', fakeAsync(() => {
    void setup();
    tick();
    fixture.componentInstance.filterForm.patchValue({ category: 'intermediate', canBuy: 'false', canSell: 'false' });
    tick(300);
    expect(stockApi.list.calls.mostRecent().args[0]).toEqual(
      jasmine.objectContaining({ category: 'intermediate', canBuy: 'false', canSell: 'false', page: 1 }),
    );
    expect(fixture.componentInstance.filtersActive).toBeTrue();
    fixture.componentInstance.clearFilters();
    tick(300);
    expect(stockApi.list.calls.mostRecent().args[0]).toEqual(
      jasmine.objectContaining({ category: undefined, canBuy: undefined, canSell: undefined }),
    );
    expect(fixture.componentInstance.filtersActive).toBeFalse();
  }));

  it('restores the filters and page of the last query when coming back from the detail (AC-08)', async () => {
    await setup({}, [ROW], (state) =>
      state.save(
        { search: 'cu', warehouseId: '', active: 'all', balance: '', category: 'finished', canBuy: '', canSell: 'true' },
        3,
      ),
    );
    expect(stockApi.list.calls.mostRecent().args[0]).toEqual(
      jasmine.objectContaining({ search: 'cu', active: 'all', category: 'finished', canSell: 'true', page: 3 }),
    );
    expect(fixture.componentInstance.filterForm.controls.category.value).toBe('finished');
  });

  it('distinguishes «sin resultados con filtros» from the initial empty state (AC-07)', async () => {
    await setup({}, []);
    expect(el().querySelector('[data-testid="stock-empty"]')).not.toBeNull();
    fixture.componentInstance.filterForm.patchValue({ canSell: 'true' }, { emitEvent: false });
    fixture.detectChanges();
    expect(el().querySelector('[data-testid="stock-no-results"]')?.textContent).toContain('Limpiar filtros');
    expect(el().querySelector('[data-testid="stock-empty"]')).toBeNull();
  });

  it('marks a negative balance with text besides color and an inactive product with a badge (AC-03, UI-03)', async () => {
    await setup({}, [{ ...ROW, quantity: '-2.000', balanceState: 'negative', productActive: false }]);
    expect(el().querySelector('[data-testid="negative-badge"]')?.textContent).toContain('Negativo');
    expect(el().querySelector('[data-testid="quantity"] .text-danger')).not.toBeNull();
    expect(el().querySelector('tbody tr')?.textContent).toContain('Inactivo');
  });

  it('links the product to its detail (AC-04)', async () => {
    await setup();
    const link = el().querySelector('[data-testid="detail-link"]') as HTMLAnchorElement;
    expect(link.getAttribute('href')).toBe('/pocketbiz/inventory/stock/p-1/w-1');
  });

  it('opens the movements of a row (AC-05)', async () => {
    await setup();
    (el().querySelector('[data-testid="open-movements"]') as HTMLButtonElement).click();
    expect(router.navigate).toHaveBeenCalledWith(['/pocketbiz/inventory/movements'], {
      queryParams: { warehouse_id: 'w-1', product_id: 'p-1' },
    });
  });

  it('explains the empty state', async () => {
    await setup({}, []);
    expect(el().querySelector('[data-testid="stock-empty"]')?.textContent).toContain('Registrar apertura');
  });

  it('shows the server error with a retry', async () => {
    await setup();
    stockApi.list.and.returnValue(throwError(() => new InventoryApiError('No se pudo conectar con el servidor.', 0)));
    fixture.componentInstance.reload();
    fixture.detectChanges();
    expect(el().querySelector('[data-testid="stock-error"]')?.textContent).toContain('No se pudo conectar');
  });

  describe('pantalla estrecha (< 992 px)', () => {
    const compactSetup = (rows: StockBalance[] = [ROW]) => setup({}, rows, undefined, true);

    it('muestra tarjetas con producto, acciones y los cinco datos, sin tabla', async () => {
      await compactSetup();
      expect(el().querySelector('table')).toBeNull();
      const card = el().querySelector('[data-testid="stock-card"]') as HTMLElement;
      expect(card.querySelector('.stock-card-header')?.textContent).toContain('Harina');
      expect(card.querySelector('.stock-card-header [data-testid="open-movements"]')).not.toBeNull();
      expect(card.querySelector('.stock-card-header [data-testid="adjust-stock"]')).not.toBeNull();
      const labels = Array.from(card.querySelectorAll('dt')).map((dt) => dt.textContent?.trim());
      expect(labels).toEqual(['Almacén', 'Clasificación', 'Usos', 'Unidad base', 'Existencia']);
      expect(card.querySelector('[data-testid="quantity"]')?.textContent).toContain('10');
      expect(card.querySelector('[data-testid="uses"]')?.textContent).toContain('Comprable');
    });

    it('marca el saldo negativo con texto en la tarjeta', async () => {
      await compactSetup([{ ...ROW, quantity: '-2.000', balanceState: 'negative' }]);
      expect(el().querySelector('[data-testid="negative-badge"]')?.textContent).toContain('Negativo');
    });

    it('el panel de filtros empieza colapsado y el botón lo abre y lo cierra', async () => {
      await compactSetup();
      const toggle = el().querySelector('[data-testid="filters-toggle"]') as HTMLButtonElement;
      expect(toggle.getAttribute('aria-expanded')).toBe('false');
      toggle.click();
      fixture.detectChanges();
      expect(toggle.getAttribute('aria-expanded')).toBe('true');
      toggle.click();
      fixture.detectChanges();
      expect(toggle.getAttribute('aria-expanded')).toBe('false');
    });

    it('no consulta al cambiar un filtro: lo hace «Aplicar», que además repliega el panel y cuenta los filtros', fakeAsync(() => {
      void setup({}, [ROW], undefined, true);
      tick();
      const calls = stockApi.list.calls.count();
      fixture.componentInstance.toggleFilters();
      fixture.componentInstance.filterForm.patchValue({ search: 'har', balance: 'zero' });
      tick(300);
      expect(stockApi.list.calls.count()).toBe(calls);
      fixture.detectChanges();
      expect(el().querySelector('[data-testid="filters-count"]')?.textContent).toContain('2');
      (el().querySelector('[data-testid="apply-filters"]') as HTMLButtonElement).click();
      tick();
      expect(stockApi.list.calls.mostRecent().args[0]).toEqual(
        jasmine.objectContaining({ search: 'har', balance: 'zero', page: 1 }),
      );
      expect(fixture.componentInstance.filtersCollapsed).toBeTrue();
    }));

    it('«Limpiar filtros» consulta con los valores por defecto', fakeAsync(() => {
      void setup({}, [ROW], undefined, true);
      tick();
      fixture.componentInstance.filterForm.patchValue({ canSell: 'true' });
      tick(300);
      fixture.componentInstance.clearFilters();
      tick(300);
      expect(stockApi.list.calls.mostRecent().args[0]).toEqual(jasmine.objectContaining({ canSell: undefined, active: 'true' }));
    }));
  });

  it('en escritorio no hay botón «Filtros» ni «Aplicar»', async () => {
    await setup();
    expect(el().querySelector('[data-testid="filters-toggle"]')).toBeNull();
    expect(el().querySelector('[data-testid="apply-filters"]')).toBeNull();
  });
});
