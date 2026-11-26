import { BreakpointObserver } from '@angular/cdk/layout';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { BehaviorSubject, of, throwError } from 'rxjs';
import Swal from 'sweetalert2';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { Page } from '../../../shared/models/page';
import { OrderApiError, OrderWarehouse, ProductionOrder } from '../models/order';
import { Recipe } from '../models/recipe';
import { OrderFiltersState, OrdersApiService } from '../services/orders-api.service';
import { RecipesApiService } from '../services/recipes-api.service';
import { OrderDetailComponent } from './order-detail/order-detail.component';
import { OrderFormComponent } from './order-form/order-form.component';
import { OrderListComponent } from './order-list/order-list.component';

const order: ProductionOrder = {
  id: 'order-1', number: 7, status: 'draft', recipe: { id: 'r-1', name: 'Cuñapé' },
  resultProduct: { id: 'p-res', name: 'Cuñapé a granel', unit: { id: 'u-1', abbreviation: 'u' } },
  warehouse: { id: 'w-1', name: 'Principal' }, preparations: 5, yieldPerPreparation: '24.0000', expectedOutput: '120.0000',
  ingredients: [{ productId: 'p-1', productName: 'Queso', unitId: 'u-2', unitAbbreviation: 'kg', quantityPerPreparation: '1.5000', expectedQuantity: '7.5000' }],
  createdAt: '2026-11-26T12:00:00Z', startedAt: null,
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
  function setup(compact = false) {
    api = jasmine.createSpyObj<OrdersApiService>('api', ['list']);
    TestBed.configureTestingModule({ imports: [OrderListComponent], providers: [...provideTestTranslations(), provideRouter([]),
      OrderFiltersState, { provide: OrdersApiService, useValue: api }, { provide: BreakpointObserver, useValue: breakpoints(compact) }] });
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
});

describe('OrderDetailComponent', () => {
  let api: jasmine.SpyObj<OrdersApiService>;
  function setup(value: ProductionOrder, compact = false) {
    api = jasmine.createSpyObj<OrdersApiService>('api', ['get', 'start']);
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

  it('below 957 px shows label|value rows and ingredient cards', () => {
    const fixture = setup(order, true);
    const root = fixture.nativeElement as HTMLElement;
    expect(root.querySelector('[data-testid="ingredient-table"]')).toBeNull();
    expect(root.querySelectorAll('[data-testid="order-info"] .order-row').length).toBe(8);
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
