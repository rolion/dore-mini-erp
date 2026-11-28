import { BreakpointObserver } from '@angular/cdk/layout';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { BehaviorSubject, Subject, of, throwError } from 'rxjs';
import Swal from 'sweetalert2';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { Page } from '../../../shared/models/page';
import { OrderApiError, OrderLot, OrderWarehouse, ProductionOrder } from '../models/order';
import { Recipe } from '../models/recipe';
import { OrderFiltersState, OrdersApiService } from '../services/orders-api.service';
import { RecipesApiService } from '../services/recipes-api.service';
import { OrderDetailComponent } from './order-detail/order-detail.component';
import { OrderFormComponent } from './order-form/order-form.component';
import { OrderRefrigerateComponent } from './order-refrigerate/order-refrigerate.component';
import { OrderListComponent } from './order-list/order-list.component';

const order: ProductionOrder = {
  id: 'order-1', number: 7, status: 'draft', recipe: { id: 'r-1', name: 'Cuñapé' },
  resultProduct: { id: 'p-res', name: 'Cuñapé a granel', unit: { id: 'u-1', abbreviation: 'u' } },
  warehouse: { id: 'w-1', name: 'Principal' }, preparations: 5, yieldPerPreparation: '24.0000', expectedOutput: '120.0000',
  ingredients: [{ productId: 'p-1', productName: 'Queso', unitId: 'u-2', unitAbbreviation: 'kg', quantityPerPreparation: '1.5000', expectedQuantity: '7.5000', actualQuantity: null }],
  createdAt: '2026-11-26T12:00:00Z', startedAt: null, actualOutput: null, enteredAt: null, lot: null, costTotal: null,
  release: null, releasedAt: null, releasedBy: null, packing: null,
};
const lotRefrigerating: OrderLot = {
  id: 'lot-1', code: 'L-20261126-0001', status: 'refrigerating', physicalQuantity: '118.0000', availableQuantity: '0.0000',
};
const started: ProductionOrder = { ...order, status: 'in_preparation', startedAt: '2026-11-26T13:00:00Z' };

const recipe: Recipe = {
  id: 'r-1', name: 'Cuñapé', yieldQuantity: '24.0000', active: true,
  resultProduct: { id: 'p-res', name: 'Cuñapé a granel', active: true, unit: { id: 'u-1', abbreviation: 'u' } },
  ingredients: [{ productId: 'p-1', productName: 'Queso', productActive: true, unitId: 'u-2', unitAbbreviation: 'kg', quantity: '1.5000' }],
  createdAt: '', updatedAt: '',
};
const warehouses: OrderWarehouse[] = [{ id: 'w-1', name: 'Principal', isDefault: true }, { id: 'w-2', name: 'Secundario', isDefault: false }];

function page<T>(results: T[]): Page<T> { return { count: results.length, next: null, previous: null, results }; }

function breakpoints(compact: boolean): jasmine.SpyObj<BreakpointObserver> {
  const spy = jasmine.createSpyObj<BreakpointObserver>('breakpoints', ['observe']);
  spy.observe.and.callFake(() => new BehaviorSubject({ matches: compact, breakpoints: {} }));
  return spy;
}

describe('OrderListComponent', () => {
  let api: jasmine.SpyObj<OrdersApiService>;
  let recipesApi: jasmine.SpyObj<RecipesApiService>;
  function setup(compact = false) {
    api = jasmine.createSpyObj<OrdersApiService>('api', ['list']);
    recipesApi = jasmine.createSpyObj<RecipesApiService>('recipesApi', ['list']);
    recipesApi.list.and.returnValue(of(page([recipe])));
    TestBed.configureTestingModule({ imports: [OrderListComponent], providers: [...provideTestTranslations(), provideRouter([]),
      OrderFiltersState, { provide: OrdersApiService, useValue: api }, { provide: RecipesApiService, useValue: recipesApi }, { provide: BreakpointObserver, useValue: breakpoints(compact) }] });
  }

  it('lists number, recipe, warehouse, preparations, output and status', () => {
    setup();
    api.list.and.returnValue(of(page([order])));
    const fixture = TestBed.createComponent(OrderListComponent);
    fixture.detectChanges();
    expect(api.list).toHaveBeenCalledWith(jasmine.objectContaining({ status: 'all', page: 1 }));
    const row = (fixture.nativeElement as HTMLElement).querySelector('[data-testid="order-row"]')?.textContent ?? '';
    for (const expected of ['OP-0007', 'Cuñapé', 'Principal', '5', '120 u', 'Borrador']) expect(row).toContain(expected);
  });

  it('below 957 px shows one card per order instead of the table', () => {
    setup(true);
    api.list.and.returnValue(of(page([started])));
    const fixture = TestBed.createComponent(OrderListComponent);
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    expect(root.querySelector('[data-testid="order-table"]')).toBeNull();
    const cards = root.querySelectorAll('[data-testid="order-card"]');
    expect(cards.length).toBe(1);
    expect(cards[0].textContent).toContain('En preparación');
  });

  it('shows the empty state and the error with retry, and applies the status filter', () => {
    setup();
    api.list.and.returnValues(of(page([])), throwError(() => new OrderApiError('Falló', 500)), of(page([])));
    const fixture = TestBed.createComponent(OrderListComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[data-testid="order-empty"]')).not.toBeNull();
    fixture.componentInstance.reload();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[role="alert"]').textContent).toContain('Falló');
    fixture.componentInstance.status.setValue('draft');
    fixture.componentInstance.applyFilters();
    expect(api.list).toHaveBeenCalledWith(jasmine.objectContaining({ status: 'draft', page: 1 }));
  });

  it('shows produced units and the bulk balance, with a dash while there is no lot', () => {  // AC-03, AC-04
    setup();
    const refrigerating: ProductionOrder = { ...started, id: 'o-2', number: 8, status: 'refrigerating', actualOutput: '118.0000', lot: lotRefrigerating };
    const released: ProductionOrder = {
      ...refrigerating, id: 'o-3', number: 9, status: 'ready_to_pack',
      lot: { ...lotRefrigerating, status: 'released', physicalQuantity: '58.0000', availableQuantity: '58.0000' },
    };
    api.list.and.returnValue(of(page([started, refrigerating, released])));
    const fixture = TestBed.createComponent(OrderListComponent);
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    const cells = (selector: string) => Array.from(root.querySelectorAll(selector)).map(cell => (cell.textContent ?? '').trim());
    expect(cells('[data-testid="row-actual"]')).toEqual(['—', '118 u', '118 u']);
    expect(cells('[data-testid="row-balance"]')).toEqual(['—', '0 u', '58 u']);
    expect(root.textContent).toContain('Listo para empacar');
  });

  it('shows produced units and balance on the compact cards', () => {  // AC-04
    setup(true);
    const cooling: ProductionOrder = { ...started, status: 'refrigerating', actualOutput: '118.0000', lot: lotRefrigerating };
    api.list.and.returnValue(of(page([cooling])));
    const fixture = TestBed.createComponent(OrderListComponent);
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    expect(root.querySelector('[data-testid="card-actual"]')?.textContent).toContain('118 u');
    expect(root.querySelector('[data-testid="card-balance"]')?.textContent).toContain('0 u');
  });

  it('filters by recipe, dates and status together, keeps them in the state and clears them', () => {  // AC-05
    setup();
    api.list.and.returnValue(of(page([order])));
    const fixture = TestBed.createComponent(OrderListComponent);
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    expect(root.querySelectorAll('#order-recipe option').length).toBe(2);
    const component = fixture.componentInstance;
    component.recipe.setValue('r-1');
    component.dateFrom.setValue('2026-11-01');
    component.dateTo.setValue('2026-11-30');
    component.status.setValue('refrigerating');
    component.applyFilters();
    expect(api.list).toHaveBeenCalledWith(jasmine.objectContaining({
      status: 'refrigerating', recipeId: 'r-1', dateFrom: '2026-11-01', dateTo: '2026-11-30', page: 1 }));
    expect(component.state.recipeId).toBe('r-1');
    component.clearFilters();
    expect(api.list).toHaveBeenCalledWith(jasmine.objectContaining({ status: 'all', recipeId: '', dateFrom: '', dateTo: '' }));
    expect(component.isDefaultFilter).toBeTrue();
  });

  it('loads every recipe page into the recipe filter', () => {  // REV-01
    setup();
    const second: Recipe = { ...recipe, id: 'r-2', name: 'Otra receta' };
    recipesApi.list.and.returnValues(of({ ...page([recipe]), next: 'p2' }), of(page([second])));
    api.list.and.returnValue(of(page([order])));
    const fixture = TestBed.createComponent(OrderListComponent);
    fixture.detectChanges();
    expect(recipesApi.list).toHaveBeenCalledWith(jasmine.objectContaining({ page: 2, pageSize: 100 }));
    expect(fixture.componentInstance.recipes.map(item => item.id)).toEqual(['r-1', 'r-2']);
  });

  it('does not query with an inverted date range and says why', () => {  // EDGE-01
    setup();
    api.list.and.returnValue(of(page([order])));
    const fixture = TestBed.createComponent(OrderListComponent);
    fixture.detectChanges();
    api.list.calls.reset();
    fixture.componentInstance.dateFrom.setValue('2026-11-30');
    fixture.componentInstance.dateTo.setValue('2026-11-01');
    fixture.componentInstance.applyFilters();
    fixture.detectChanges();
    expect(api.list).not.toHaveBeenCalled();
    expect(fixture.nativeElement.querySelector('[data-testid="range-error"]')).not.toBeNull();
  });

  it('with filters and no results shows each active filter and the clear button', () => {  // AC-05, EDGE-04
    setup();
    api.list.and.returnValue(of(page([])));
    const fixture = TestBed.createComponent(OrderListComponent);
    fixture.detectChanges();
    fixture.componentInstance.recipe.setValue('r-1');
    fixture.componentInstance.dateFrom.setValue('2026-11-01');
    fixture.componentInstance.applyFilters();
    fixture.detectChanges();
    const active = (fixture.nativeElement as HTMLElement).querySelector('[data-testid="active-filters"]')?.textContent ?? '';
    expect(active).toContain('Cuñapé');
    expect(active).toContain('2026-11-01');
    expect(fixture.nativeElement.querySelector('[data-testid="clear-filters"]').disabled).toBeFalse();
  });
});

describe('OrderDetailComponent', () => {
  let api: jasmine.SpyObj<OrdersApiService>;
  function setup(value: ProductionOrder, compact = false) {
    api = jasmine.createSpyObj<OrdersApiService>('api', ['get', 'start', 'release', 'pack']);
    api.get.and.returnValue(of(value));
    TestBed.configureTestingModule({ imports: [OrderDetailComponent], providers: [...provideTestTranslations(), provideRouter([]),
      { provide: OrdersApiService, useValue: api }, { provide: BreakpointObserver, useValue: breakpoints(compact) },
      { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: 'order-1' }) } } }] });
    const fixture = TestBed.createComponent(OrderDetailComponent);
    fixture.detectChanges();
    return fixture;
  }

  it('shows data, expected totals and Start/Edit actions in draft', () => {
    const fixture = setup(order);
    const root = fixture.nativeElement as HTMLElement;
    expect(root.querySelector('[data-testid="order-number"]')?.textContent).toContain('OP-0007');
    expect(root.querySelector('[data-testid="detail-output"]')?.textContent).toContain('120 u');
    expect(root.querySelector('[data-testid="ingredient-row"]')?.textContent).toContain('7.5 kg');
    expect(root.querySelector('[data-testid="start"]')).not.toBeNull();
    expect(root.querySelector('[data-testid="edit"]')).not.toBeNull();
  });

  it('hides Start and Edit once in preparation and shows the start date', () => {
    const fixture = setup(started);
    const root = fixture.nativeElement as HTMLElement;
    expect(root.querySelector('[data-testid="start"]')).toBeNull();
    expect(root.querySelector('[data-testid="edit"]')).toBeNull();
    expect(root.querySelector('[data-testid="started-at"]')?.textContent).not.toContain('—');
  });

  it('offers Pass to refrigeration only while in preparation', () => {
    const preparing = setup(started).nativeElement as HTMLElement;
    expect(preparing.querySelector('[data-testid="refrigerate"]')).not.toBeNull();
    expect(preparing.querySelector('[data-testid="registered"]')).toBeNull();
  });

  it('shows the lot stock: physical, available and status, by state', () => {  // AC-06, UI-02
    const released: ProductionOrder = {
      ...started, status: 'ready_to_pack', actualOutput: '118.0000', enteredAt: '2026-11-26T15:00:00Z',
      lot: { ...lotRefrigerating, status: 'released', physicalQuantity: '58.0000', availableQuantity: '58.0000' },
      release: { minHours: 12, releasableFrom: '2026-11-27T03:00:00Z', canRelease: false }, releasedAt: '2026-11-27T04:00:00Z', releasedBy: 'ana',
    };
    TestBed.resetTestingModule();
    const root = setup(released).nativeElement as HTMLElement;
    expect(root.querySelector('[data-testid="lot-status"]')?.textContent).toContain('Liberado');
    expect(root.querySelector('[data-testid="lot-bulk"]')?.textContent).toContain('58 u');
    expect(root.querySelector('[data-testid="release-progress"]')).toBeNull();  // tras liberar ya no hay cuenta regresiva
    expect(root.querySelector('[data-testid="releasable-from"]')).toBeNull();
    expect(root.querySelector('[data-testid="release"]')).toBeNull();
    expect(root.querySelector('[data-testid="refrigerate"]')).toBeNull();
    expect(root.querySelector('[data-testid="start"]')).toBeNull();
  });

  it('shows no lot stock section before the lot exists', () => {  // AC-06
    const root = setup(started).nativeElement as HTMLElement;
    expect(root.querySelector('[data-testid="lot-stock"]')).toBeNull();
  });

  it('shows dashes when Inventory no longer has the lot', () => {  // EDGE-02
    const missing: ProductionOrder = {
      ...started, status: 'refrigerating', actualOutput: '118.0000', enteredAt: '2026-11-26T15:00:00Z',
      lot: { ...lotRefrigerating, status: null, physicalQuantity: null, availableQuantity: null },
      release: { minHours: 12, releasableFrom: '2026-11-27T03:00:00Z', canRelease: false },
    };
    const root = setup(missing).nativeElement as HTMLElement;
    expect(root.querySelector('[data-testid="lot-bulk"]')?.textContent?.trim()).toBe('—');
  });

  describe('layout (DDR detalle-orden-rediseno)', () => {
    const cooling: ProductionOrder = {
      ...started, status: 'refrigerating', actualOutput: '20.0000', enteredAt: new Date(Date.now() - 30 * 60000).toISOString(),
      lot: lotRefrigerating, costTotal: '18.65',
      ingredients: [
        { ...started.ingredients[0], actualQuantity: '7.0000' },
        { ...started.ingredients[0], productId: 'p-2', productName: 'Almidón', unitAbbreviation: 'gr', quantityPerPreparation: '20.0000', expectedQuantity: '20.0000', actualQuantity: '20.0000' },
      ],
      release: { minHours: 1, releasableFrom: new Date(Date.now() + 30 * 60000).toISOString(), canRelease: false },
    };

    it('shows the status badge and recipe · product · warehouse in the header', () => {  // UI-02, AC-08
      TestBed.resetTestingModule();
      const root = setup(cooling).nativeElement as HTMLElement;
      expect(root.querySelector('[data-testid="order-status"]')?.textContent).toContain('En refrigeración');
      const subtitle = root.querySelector('[data-testid="order-subtitle"]')?.textContent ?? '';
      for (const part of ['Cuñapé', 'Cuñapé a granel', 'Principal']) expect(subtitle).toContain(part);
    });

    it('marks done, current and pending stages with their dates', () => {  // AC-08
      TestBed.resetTestingModule();
      const root = setup(cooling).nativeElement as HTMLElement;
      const steps = Array.from(root.querySelectorAll('[data-testid="order-step"]'));
      expect(steps.map(step => step.classList.contains('is-done'))).toEqual([true, true, false, false]);
      expect(steps.map(step => step.getAttribute('aria-current'))).toEqual([null, null, 'step', null]);
      expect(steps[3].textContent).toContain('—');
      expect(steps[0].textContent).toContain('26/11/2026');
    });

    it('shows a draft with only the first stage current', () => {  // AC-08
      TestBed.resetTestingModule();
      const steps = Array.from((setup(order).nativeElement as HTMLElement).querySelectorAll('[data-testid="order-step"]'));
      expect(steps.map(step => step.getAttribute('aria-current'))).toEqual(['step', null, null, null]);
    });

    it('marks every stage done once the order is ready to pack', () => {  // AC-08
      TestBed.resetTestingModule();
      const ready: ProductionOrder = { ...cooling, status: 'ready_to_pack', releasedAt: '2026-11-27T04:00:00Z', releasedBy: 'ana',
        lot: { ...lotRefrigerating, status: 'released', availableQuantity: '20.0000' } };
      const steps = Array.from((setup(ready).nativeElement as HTMLElement).querySelectorAll('[data-testid="order-step"]'));
      expect(steps.every(step => step.classList.contains('is-done'))).toBeTrue();
    });

    it('shows the key figures once and the release progress toward the minimum', () => {  // UI-02, UI-04
      TestBed.resetTestingModule();
      const root = setup(cooling).nativeElement as HTMLElement;
      expect(root.querySelector('[data-testid="actual-output"]')?.textContent).toContain('20 u');
      expect(root.querySelector('[data-testid="lot-bulk"]')?.textContent).toContain('118 u');  // físico, aún bloqueado
      expect(root.querySelector('[data-testid="lot-stock"]')).not.toBeNull();
      expect(root.querySelector('[data-testid="packed"]')).toBeNull();
      expect(root.querySelector('[data-testid="cost"]')?.textContent).toContain('18.65');
      const bar = root.querySelector('[data-testid="release-progress"]');
      expect(bar?.getAttribute('role')).toBe('progressbar');
      expect(Number(bar?.getAttribute('aria-valuenow'))).toBeGreaterThanOrEqual(45);
      expect(Number(bar?.getAttribute('aria-valuenow'))).toBeLessThanOrEqual(55);
      expect(bar?.getAttribute('aria-valuetext')).toMatch(/\d/);  // REV-04: texto legible para lectores de pantalla
      expect(root.querySelector('[data-testid="release"]')?.getAttribute('aria-describedby')).toBe('release-hint');
      expect(root.querySelector('#release-hint')).not.toBeNull();
    });

    it('shows the difference between actual and planned consumption only where it differs', () => {  // AC-06
      TestBed.resetTestingModule();
      const root = setup(cooling).nativeElement as HTMLElement;
      const cells = Array.from(root.querySelectorAll('[data-testid="difference"]')).map(cell => (cell.textContent ?? '').trim());
      expect(cells).toEqual(['−0.5 kg', '—']);
    });
  });

  it('shows the recorded production, lot and actual consumption once refrigerating', () => {
    const done: ProductionOrder = {
      ...started, status: 'refrigerating', actualOutput: '118.0000', enteredAt: '2026-11-26T15:00:00Z',
      lot: { ...lotRefrigerating, code: 'L-20261126-0001' }, costTotal: null,
      ingredients: [{ ...started.ingredients[0], actualQuantity: '7.0000' }],
    };
    TestBed.resetTestingModule();
    const root = setup(done).nativeElement as HTMLElement;
    expect(root.querySelector('[data-testid="refrigerate"]')).toBeNull();
    expect(root.querySelector('[data-testid="actual-output"]')?.textContent).toContain('118');
    expect(root.querySelector('[data-testid="lot-code"]')?.textContent).toContain('L-20261126-0001');
    expect(root.querySelector('[data-testid="cost"]')?.textContent).toContain('Sin costo');
    expect(root.querySelector('[data-testid="actual-quantity"]')?.textContent).toContain('7 kg');
  });

  describe('packing', () => {
    const ready = (bulk: string): ProductionOrder => ({
      ...started, status: 'ready_to_pack', actualOutput: '118.0000', enteredAt: '2026-11-26T14:00:00Z',
      lot: { id: 'lot-1', code: 'L-20261127-0001', status: 'released', physicalQuantity: bulk, availableQuantity: bulk }, releasedAt: '2026-11-27T10:00:00Z', releasedBy: 'Ana',
      packing: { unitsPerPack: 6, suggestedBagPerPack: '0.1700', labelsPerPack: 1, bulkAvailable: bulk, bulkUnitAbbreviation: 'u', packings: [] },
    });

    it('shows the bulk balance, an empty history and an enabled action when a pack fits', () => {  // AC-08, UI-01, UI-03
      const root: HTMLElement = setup(ready('82.0000')).nativeElement;
      expect(root.querySelector('[data-testid="lot-bulk"]')?.textContent).toContain('82');
      expect(root.querySelector('[data-testid="packed"]')).toBeNull();
      expect(root.querySelector('[data-testid="packing-empty"]')).not.toBeNull();
      expect((root.querySelector('[data-testid="pack"]') as HTMLButtonElement).disabled).toBeFalse();
      expect(root.querySelector('[data-testid="pack-hint"]')).toBeNull();
    });

    it('disables the action and explains it when less than one pack is left', () => {  // AC-08, UI-03, EDGE-04
      const root: HTMLElement = setup(ready('5.0000')).nativeElement;
      expect((root.querySelector('[data-testid="pack"]') as HTMLButtonElement).disabled).toBeTrue();
      expect(root.querySelector('[data-testid="pack-hint"]')).not.toBeNull();
    });

    it('lists the history of packings with lot, quantities and cost', () => {  // AC-04, AC-08, UI-01
      const value = ready('82.0000');
      value.packing = { ...value.packing!, packings: [{
        id: 'k-1', number: 1, packs: 6, packProduct: { id: 'p-pack', name: 'Pack x6', unit: 'u' }, bagProduct: { id: 'p-bag', name: 'Bolsa', unit: 'm' },
        labelProduct: null, labelsQuantity: '0.0000', bulkQuantity: '36.0000', bagsQuantity: '1.0200', bagPerPack: '0.1700', lot: { id: 'lot-1', code: 'L-20261127-0001' },
        costTotal: '39.00', unitCost: '6.500000', createdAt: '2026-11-27T11:00:00Z', createdBy: 'Ana' }] };
      const root: HTMLElement = setup(value).nativeElement;
      const row = root.querySelector('[data-testid="packing-row"]')?.textContent ?? '';
      expect(row).toContain('Pack x6');
      expect(row).toContain('L-20261127-0001');
      expect(row).toContain('36');
      expect(row).toContain('Ana');
      expect(row).toContain('1.02 m');  // la bolsa lleva su unidad
      expect(row).toContain('6.50');  // costo unitario por pack
      expect(root.querySelector('[data-testid="packed"]')?.textContent).toContain('36 u');
      expect(root.querySelector('[data-testid="packed-packs"]')?.textContent).toContain('6');
    });

    it('adds up several packings in the Packed figure', () => {  // AC-04, UI-01
      const entry = (id: string, number: number, packs: number, bulk: string) => ({
        id, number, packs, packProduct: { id: 'p-pack', name: 'Pack x6', unit: 'u' }, bagProduct: { id: 'p-bag', name: 'Bolsa', unit: 'm' },
        labelProduct: null, labelsQuantity: '0.0000', bulkQuantity: bulk, bagsQuantity: '1.0200', bagPerPack: '0.1700',
        lot: { id: 'lot-1', code: 'L-20261127-0001' }, costTotal: null, unitCost: null, createdAt: '2026-11-27T11:00:00Z', createdBy: 'Ana' });
      const value = ready('64.0000');
      value.packing = { ...value.packing!, packings: [entry('k-1', 1, 6, '36.0000'), entry('k-2', 2, 3, '18.0000')] };
      const root: HTMLElement = setup(value).nativeElement;
      expect(root.querySelector('[data-testid="packed"]')?.textContent).toContain('54 u');
      expect(root.querySelector('[data-testid="packed-packs"]')?.textContent).toContain('9');
      expect(root.querySelectorAll('[data-testid="packing-row"]').length).toBe(2);
    });

    it('stacks the history as cards on narrow screens', () => {  // AC-04, UI-01
      const value = ready('82.0000');
      value.packing = { ...value.packing!, packings: [{
        id: 'k-1', number: 1, packs: 6, packProduct: { id: 'p-pack', name: 'Pack x6', unit: 'u' }, bagProduct: { id: 'p-bag', name: 'Bolsa', unit: 'm' },
        labelProduct: null, labelsQuantity: '0.0000', bulkQuantity: '36.0000', bagsQuantity: '1.0200', bagPerPack: '0.1700', lot: { id: 'lot-1', code: 'L-20261127-0001' },
        costTotal: null, unitCost: null, createdAt: '2026-11-27T11:00:00Z', createdBy: 'Ana' }] };
      const root: HTMLElement = setup(value, true).nativeElement;
      expect(root.querySelector('[data-testid="packing-table"]')).toBeNull();
      const card = root.querySelector('[data-testid="packing-card"]')?.textContent ?? '';
      expect(card).toContain('Pack x6');
      expect(card).toContain('L-20261127-0001');
      expect(card).toContain('Ana');
    });

    it('has no packing section or action outside ready_to_pack', () => {  // AC-08, UI-03
      const root: HTMLElement = setup(started).nativeElement;
      expect(root.querySelector('[data-testid="packing-section"]')).toBeNull();
      expect(root.querySelector('[data-testid="pack"]')).toBeNull();
    });
  });

  describe('release', () => {
    const entered = new Date(Date.now() - 2 * 3600 * 1000).toISOString();
    const refrigerating = (hoursAfter: number): ProductionOrder => ({
      ...started, status: 'refrigerating', actualOutput: '118.0000', enteredAt: entered,
      lot: { ...lotRefrigerating, code: 'L-20261127-0001' }, ingredients: [{ ...started.ingredients[0], actualQuantity: '7.0000' }],
      release: { minHours: 12, canRelease: hoursAfter < 0,
        releasableFrom: new Date(Date.parse(entered) + 12 * 3600 * 1000 + hoursAfter * 3600 * 1000).toISOString() },
    });

    it('shows entry, elapsed time, minimum and the first eligible time, with Release disabled before it', () => {  // AC-01, UI-01, UI-02
      TestBed.resetTestingModule();
      const root = setup(refrigerating(0)).nativeElement as HTMLElement;
      expect(root.querySelector('[data-testid="release-section"]')).not.toBeNull();
      expect(root.querySelector('[data-testid="elapsed"]')?.textContent).toContain('2 h');
      expect(root.querySelector('[data-testid="min-hours"]')?.textContent).toContain('12');
      expect(root.querySelector('[data-testid="releasable-from"]')?.textContent).not.toContain('—');
      expect((root.querySelector('[data-testid="release"]') as HTMLButtonElement).disabled).toBeTrue();
      expect(root.querySelector('[data-testid="release-hint"]')).not.toBeNull();
    });

    it('enables Release once the first eligible time has passed', () => {  // UI-02
      TestBed.resetTestingModule();
      const root = setup(refrigerating(-11)).nativeElement as HTMLElement;
      expect((root.querySelector('[data-testid="release"]') as HTMLButtonElement).disabled).toBeFalse();
      expect(root.querySelector('[data-testid="release-hint"]')).toBeNull();
    });

    it('confirms and then shows who released and when', async () => {  // AC-03, AC-04
      TestBed.resetTestingModule();
      const fixture = setup(refrigerating(-11));
      const released: ProductionOrder = { ...refrigerating(-11), status: 'ready_to_pack', releasedAt: new Date().toISOString(), releasedBy: 'Ana' };
      api.release.and.returnValue(of(released));
      spyOn(Swal, 'fire').and.resolveTo({ isConfirmed: true } as never);
      await fixture.componentInstance.release();
      fixture.detectChanges();
      const root = fixture.nativeElement as HTMLElement;
      expect(api.release).toHaveBeenCalledOnceWith('order-1');
      expect(root.querySelector('[data-testid="released-by"]')?.textContent).toContain('Ana');
      expect(root.querySelector('[data-testid="release"]')).toBeNull();
      expect(root.querySelector('[data-testid="success"]')).not.toBeNull();
    });

    it('does not release when the confirmation is cancelled', async () => {
      TestBed.resetTestingModule();
      const fixture = setup(refrigerating(-11));
      spyOn(Swal, 'fire').and.resolveTo({ isConfirmed: false } as never);
      await fixture.componentInstance.release();
      expect(api.release).not.toHaveBeenCalled();
    });

    it('shows the server rejection with the first eligible time', async () => {  // AC-02
      TestBed.resetTestingModule();
      const fixture = setup(refrigerating(-11));
      api.release.and.returnValue(throwError(() => new OrderApiError('x', 409,
        { code: 'release_too_early', releasableFrom: '2026-11-27T20:00:00Z' })));
      spyOn(Swal, 'fire').and.resolveTo({ isConfirmed: true } as never);
      await fixture.componentInstance.release();
      fixture.detectChanges();
      expect((fixture.nativeElement as HTMLElement).querySelector('[data-testid="action-error"]')?.textContent).toContain('2026');
      expect(api.get).toHaveBeenCalledTimes(2);
    });
  });

  it('formats the total cost as money when there is one', () => {  // REV-03
    const costed: ProductionOrder = {
      ...started, status: 'refrigerating', actualOutput: '118.0000', enteredAt: '2026-11-26T15:00:00Z',
      lot: { ...lotRefrigerating, code: 'L-20261126-0001' }, costTotal: '95.00',
      ingredients: [{ ...started.ingredients[0], actualQuantity: '7.0000' }],
    };
    TestBed.resetTestingModule();
    const root = setup(costed).nativeElement as HTMLElement;
    expect(root.querySelector('[data-testid="cost"]')?.textContent).toContain('Bs 95.00');
  });

  it('below 957 px shows ingredient cards instead of the table and keeps the order data rows', () => {
    const fixture = setup(order, true);
    const root = fixture.nativeElement as HTMLElement;
    expect(root.querySelector('[data-testid="ingredient-table"]')).toBeNull();
    expect(root.querySelectorAll('[data-testid="order-data"] .order-row').length).toBe(6);
    const card = root.querySelector('[data-testid="ingredient-card"]')?.textContent ?? '';
    expect(card).toContain('Queso');
    expect(card).toContain('1.5 kg');
    expect(card).toContain('7.5 kg');
  });

  it('confirms before starting and then shows the started order', async () => {
    const fixture = setup(order);
    api.start.and.returnValue(of(started));
    const fire = spyOn(Swal, 'fire').and.resolveTo({ isConfirmed: true } as never);
    await fixture.componentInstance.start();
    fixture.detectChanges();
    expect(fire).toHaveBeenCalled();
    expect(api.start).toHaveBeenCalledWith('order-1');
    expect(fixture.componentInstance.order?.status).toBe('in_preparation');
    expect(fixture.nativeElement.querySelector('[data-testid="start"]')).toBeNull();
  });

  it('does not start when the confirmation is cancelled', async () => {
    const fixture = setup(order);
    spyOn(Swal, 'fire').and.resolveTo({ isConfirmed: false } as never);
    await fixture.componentInstance.start();
    expect(api.start).not.toHaveBeenCalled();
  });
});

describe('OrderFormComponent', () => {
  let api: jasmine.SpyObj<OrdersApiService>;
  let recipes: jasmine.SpyObj<RecipesApiService>;
  function create(id: string | null = null, compact = false) {
    TestBed.configureTestingModule({ imports: [OrderFormComponent], providers: [...provideTestTranslations(), provideRouter([]),
      { provide: BreakpointObserver, useValue: breakpoints(compact) },
      { provide: OrdersApiService, useValue: api }, { provide: RecipesApiService, useValue: recipes },
      { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap(id ? { id } : {}) } } }] });
    const fixture = TestBed.createComponent(OrderFormComponent);
    fixture.detectChanges();
    return fixture;
  }
  beforeEach(() => {
    api = jasmine.createSpyObj<OrdersApiService>('api', ['get', 'create', 'update', 'start', 'warehouses']);
    recipes = jasmine.createSpyObj<RecipesApiService>('recipes', ['list']);
    api.warehouses.and.returnValue(of(warehouses));
    recipes.list.and.returnValue(of(page([recipe])));
  });

  it('loads only active recipes, preselects the default warehouse and previews 24 x 5 = 120', () => {
    const fixture = create();
    const component = fixture.componentInstance;
    expect(recipes.list).toHaveBeenCalledWith(jasmine.objectContaining({ status: 'active' }));
    expect(component.form.controls.warehouse.value?.id).toBe('w-1');
    component.form.controls.recipe.setValue(recipe);
    component.form.controls.preparations.setValue('5');
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    expect(root.querySelector('[data-testid="preview-output"]')?.textContent).toContain('120 u de Cuñapé a granel');
    const row = root.querySelector('[data-testid="preview-row"]')?.textContent ?? '';
    expect(row).toContain('1.5 kg');
    expect(row).toContain('7.5 kg');
    component.form.controls.preparations.setValue('2.5');
    fixture.detectChanges();
    expect(root.querySelector('[data-testid="preview-empty"]')).not.toBeNull();
  });

  it('below 957 px previews ingredients as cards', () => {
    const fixture = create(null, true);
    fixture.componentInstance.form.controls.recipe.setValue(recipe);
    fixture.componentInstance.form.controls.preparations.setValue('3');
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    expect(root.querySelector('[data-testid="preview-table"]')).toBeNull();
    expect(root.querySelector('[data-testid="preview-card"]')?.textContent).toContain('4.5 kg');
  });

  it('blocks an invalid submit and shows field errors', () => {
    const fixture = create();
    fixture.componentInstance.saveDraft();
    fixture.detectChanges();
    expect(api.create).not.toHaveBeenCalled();
    expect(fixture.nativeElement.querySelector('[data-testid="recipe-error"]')).not.toBeNull();
    expect(fixture.nativeElement.querySelector('[data-testid="preparations-error"]')).not.toBeNull();
  });

  it('saves a draft and goes to the detail', () => {
    api.create.and.returnValue(of(order));
    const fixture = create();
    const navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
    fixture.componentInstance.form.controls.recipe.setValue(recipe);
    fixture.componentInstance.form.controls.preparations.setValue('5');
    fixture.componentInstance.saveDraft();
    expect(api.create).toHaveBeenCalledWith({ recipeId: 'r-1', warehouseId: 'w-1', preparations: 5 });
    expect(api.start).not.toHaveBeenCalled();
    expect(navigate).toHaveBeenCalledWith(['/pocketbiz/production/orders', 'order-1']);
  });

  it('saves and starts with Iniciar preparación', () => {
    api.create.and.returnValue(of(order));
    api.start.and.returnValue(of(started));
    const fixture = create();
    const navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
    fixture.componentInstance.form.controls.recipe.setValue(recipe);
    fixture.componentInstance.form.controls.preparations.setValue('5');
    fixture.componentInstance.startPreparation();
    expect(api.create).toHaveBeenCalled();
    expect(api.start).toHaveBeenCalledWith('order-1');
    expect(navigate).toHaveBeenCalledWith(['/pocketbiz/production/orders', 'order-1']);
  });

  it('keeps what was typed, shows server errors by field and retries as an update after a failed start', () => {
    api.create.and.returnValue(throwError(() => new OrderApiError('Revisa', 400,
      { recipeId: 'Receta inactiva.', preparations: 'Demasiadas.' })));
    const fixture = create();
    const component = fixture.componentInstance;
    component.form.controls.recipe.setValue(recipe);
    component.form.controls.preparations.setValue('5');
    component.saveDraft();
    fixture.detectChanges();
    expect(component.form.controls.preparations.value).toBe('5');
    expect(fixture.nativeElement.querySelector('[data-testid="recipe-error"]').textContent).toContain('Receta inactiva.');
    expect(fixture.nativeElement.querySelector('[data-testid="preparations-error"]').textContent).toContain('Demasiadas.');
    expect(fixture.nativeElement.querySelector('[data-testid="form-error"]').textContent).toContain('Revisa');

    api.create.and.returnValue(of(order));
    api.start.and.returnValue(throwError(() => new OrderApiError('Revisa', 400, { warehouseId: 'Almacén inactivo.' })));
    api.update.and.returnValue(of(order));
    component.startPreparation();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[data-testid="warehouse-error"]').textContent).toContain('Almacén inactivo.');
    component.startPreparation();
    expect(api.update).toHaveBeenCalledWith('order-1', { warehouseId: 'w-1', preparations: 5 });
  });

  it('warns and blocks the buttons without active recipes or warehouses', () => {
    recipes.list.and.returnValue(of(page<Recipe>([])));
    api.warehouses.and.returnValue(of([]));
    const fixture = create();
    const root = fixture.nativeElement as HTMLElement;
    expect(root.querySelector('[data-testid="no-recipes"]')).not.toBeNull();
    expect(root.querySelector('[data-testid="no-warehouses"]')).not.toBeNull();
    expect((root.querySelector('[data-testid="save-draft"]') as HTMLButtonElement).disabled).toBeTrue();
    expect((root.querySelector('[data-testid="start"]') as HTMLButtonElement).disabled).toBeTrue();
  });

  it('edits a draft with a read-only recipe, previews from its copy and updates with PUT', () => {
    api.get.and.returnValue(of(order));
    api.update.and.returnValue(of(order));
    const fixture = create('order-1');
    const navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
    const component = fixture.componentInstance;
    const root = fixture.nativeElement as HTMLElement;
    expect(recipes.list).not.toHaveBeenCalled();
    expect(root.querySelector('[data-testid="recipe-readonly"]')?.textContent).toContain('Cuñapé');
    expect(component.form.controls.preparations.value).toBe('5');
    expect(component.hasUnsavedChanges()).toBeFalse();
    component.form.controls.preparations.setValue('10');
    fixture.detectChanges();
    expect(root.querySelector('[data-testid="preview-output"]')?.textContent).toContain('240 u');
    component.saveDraft();
    expect(api.update).toHaveBeenCalledWith('order-1', { warehouseId: 'w-1', preparations: 10 });
    expect(navigate).toHaveBeenCalledWith(['/pocketbiz/production/orders', 'order-1']);
  });

  it('redirects to the detail when the order is no longer a draft', () => {
    api.get.and.returnValue(of(started));
    const fixture = create('order-1');
    const navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
    fixture.componentInstance.ngOnInit();
    expect(navigate).toHaveBeenCalledWith(['/pocketbiz/production/orders', 'order-1']);
  });
});


describe('OrderRefrigerateComponent', () => {
  let api: jasmine.SpyObj<OrdersApiService>;
  let router: Router;
  function setup(value: ProductionOrder = started) {
    api = jasmine.createSpyObj<OrdersApiService>('api', ['get', 'refrigerate']);
    api.get.and.returnValue(of(value));
    TestBed.configureTestingModule({ imports: [OrderRefrigerateComponent], providers: [...provideTestTranslations(), provideRouter([]),
      { provide: OrdersApiService, useValue: api },
      { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: 'order-1' }) } } }] });
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    const fixture = TestBed.createComponent(OrderRefrigerateComponent);
    fixture.detectChanges();
    return fixture;
  }
  const inputs = (root: HTMLElement) => ({
    output: root.querySelector<HTMLInputElement>('[data-testid="actual-output"]') as HTMLInputElement,
    line: root.querySelector<HTMLInputElement>('[data-testid="line-input"]') as HTMLInputElement,
    submit: root.querySelector<HTMLButtonElement>('[data-testid="submit"]') as HTMLButtonElement,
  });
  const type = (input: HTMLInputElement, value: string) => { input.value = value; input.dispatchEvent(new Event('input')); };

  it('proposes the planned quantities and lets the operator correct them', () => {  // AC-01, AC-11
    const fixture = setup();
    const root = fixture.nativeElement as HTMLElement;
    const { output, line } = inputs(root);
    expect(output.value).toBe('120');
    expect(line.value).toBe('7.5');
    type(output, '118');
    type(line, '7');
    api.refrigerate.and.returnValue(of({ ...started, status: 'refrigerating' }));
    fixture.componentInstance.submit();
    expect(api.refrigerate).toHaveBeenCalledWith('order-1', jasmine.objectContaining({
      actualOutput: '118', ingredients: [{ productId: 'p-1', actualQuantity: '7' }] }));
    expect(router.navigate).toHaveBeenCalledWith(['/pocketbiz/production/orders', 'order-1']);
  });

  it('does not submit invalid quantities', () => {  // AC-06
    const fixture = setup();
    const root = fixture.nativeElement as HTMLElement;
    const { output, line } = inputs(root);
    type(output, '0');
    type(line, '-1');
    fixture.componentInstance.submit();
    fixture.detectChanges();
    expect(api.refrigerate).not.toHaveBeenCalled();
    expect(root.querySelector('[data-testid="output-error"]')).not.toBeNull();
    expect(root.querySelector('[data-testid="line-error"]')).not.toBeNull();
  });

  it('ignores a second submit while the first is in flight', () => {  // AC-04
    const fixture = setup();
    api.refrigerate.and.returnValue(new Subject<ProductionOrder>());
    fixture.componentInstance.submit();
    fixture.componentInstance.submit();
    fixture.detectChanges();
    expect(api.refrigerate).toHaveBeenCalledTimes(1);
    expect(inputs(fixture.nativeElement as HTMLElement).submit.disabled).toBeTrue();
  });

  it('shows the shortage on the affected row and keeps what was typed', () => {  // AC-03
    const fixture = setup();
    const root = fixture.nativeElement as HTMLElement;
    type(inputs(root).line, '9');
    api.refrigerate.and.returnValue(throwError(() => new OrderApiError('x', 409, { code: 'insufficient_stock' }, false, [
      { productId: 'p-1', productName: 'Queso', unitAbbreviation: 'kg', requested: '9.0000', available: '5.0000', missing: '4.0000' }])));
    fixture.componentInstance.submit();
    fixture.detectChanges();
    expect(root.querySelector('[data-testid="form-error"]')?.textContent).toContain('No hay existencias suficientes');
    expect(root.querySelector('[data-testid="shortage"]')?.textContent).toContain('Falta 4 kg (hay 5)');
    expect(inputs(root).line.value).toBe('9');
    expect(router.navigate).not.toHaveBeenCalled();
    expect(fixture.componentInstance.saving).toBeFalse();
  });

  it('marks the row the server flagged and keeps what was typed', () => {  // REV-03
    const fixture = setup();
    const root = fixture.nativeElement as HTMLElement;
    type(inputs(root).line, '9.5');
    api.refrigerate.and.returnValue(throwError(() => new OrderApiError('x', 400, {
      ingredientLines: ['Este ingrediente solo admite cantidades enteras.'] })));
    fixture.componentInstance.submit();
    fixture.detectChanges();
    expect(root.querySelector('[data-testid="line-server-error"]')?.textContent).toContain('solo admite cantidades enteras');
    expect(root.querySelector('.short-row')).not.toBeNull();
    expect(inputs(root).line.value).toBe('9.5');
  });

  it('leaves for the detail when the order is not in preparation', () => {
    setup(order);
    expect(router.navigate).toHaveBeenCalledWith(['/pocketbiz/production/orders', 'order-1']);
  });
});
