import { BreakpointObserver } from '@angular/cdk/layout';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { BehaviorSubject, of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { Page } from '../../../shared/models/page';
import { Product } from '../../products/models/product';
import { ProductsApiService } from '../../products/services/products-api.service';
import { Recipe, RecipeApiError } from '../models/recipe';
import { RecipeFiltersState, RecipesApiService } from '../services/recipes-api.service';
import { COMPACT_QUERY, RecipeDetailComponent } from './recipe-detail/recipe-detail.component';
import { RecipeFormComponent, positiveQuantity } from './recipe-form/recipe-form.component';
import { RecipeListComponent } from './recipe-list/recipe-list.component';

const recipe: Recipe = {
  id: 'recipe-1', name: 'Queso', yieldQuantity: '24.0000', active: true,
  resultProduct: { id: 'p-res', name: 'Cuñapé a granel', active: true, unit: { id: 'u-1', abbreviation: 'u' } },
  ingredients: [{ productId: 'p-1', productName: 'Queso', productActive: true, unitId: 'u-2', unitAbbreviation: 'kg', quantity: '1.5000' }],
  createdAt: '2026-11-26T12:00:00Z', updatedAt: '2026-11-26T12:00:00Z',
};

function page(results: Recipe[]): Page<Recipe> { return { count: results.length, next: null, previous: null, results }; }

function product(id: string, name: string, unitId: string, abbreviation: string): Product {
  return { id, name, description: '', salePrice: null, category: null, canBuy: true, canSell: false, needsReview: false, active: true,
    tracksStock: true, baseUnit: { id: unitId, name: abbreviation, abbreviation, allowsFractions: true }, createdAt: '', updatedAt: '' };
}

describe('positiveQuantity', () => {
  it('accepts positive decimals up to 4 places only', () => {
    const check = (value: string) => positiveQuantity({ value } as never);
    expect(check('24')).toBeNull();
    expect(check('0.0001')).toBeNull();
    expect(check('0')).toEqual({ positive: true });
    expect(check('1.00001')).toEqual({ decimal: true });
    expect(check('-1')).toEqual({ decimal: true });
    expect(check('')).toEqual({ required: true });
  });
});

describe('RecipeListComponent', () => {
  let api: jasmine.SpyObj<RecipesApiService>;
  beforeEach(() => {
    api = jasmine.createSpyObj<RecipesApiService>('api', ['list']);
    TestBed.configureTestingModule({ imports: [RecipeListComponent], providers: [...provideTestTranslations(), provideRouter([]),
      RecipeFiltersState, { provide: RecipesApiService, useValue: api }] });
  });

  it('lists recipe, product, yield with unit and status, active by default', () => {
    api.list.and.returnValue(of(page([recipe])));
    const fixture = TestBed.createComponent(RecipeListComponent);
    fixture.detectChanges();
    expect(api.list).toHaveBeenCalledWith(jasmine.objectContaining({ status: 'active', page: 1 }));
    const row = (fixture.nativeElement as HTMLElement).querySelector('[data-testid="recipe-row"]')?.textContent ?? '';
    expect(row).toContain('Queso');
    expect(row).toContain('Cuñapé a granel');
    expect(row).toContain('24 u');
  });

  it('shows the empty state and the error with retry', () => {
    api.list.and.returnValues(of(page([])), throwError(() => new RecipeApiError('Falló', 500)));
    const fixture = TestBed.createComponent(RecipeListComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[data-testid="recipe-empty"]')).not.toBeNull();
    fixture.componentInstance.reload();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[role="alert"]').textContent).toContain('Falló');
  });

  it('applies the status filter and resets the page', () => {
    api.list.and.returnValue(of(page([])));
    const fixture = TestBed.createComponent(RecipeListComponent);
    fixture.detectChanges();
    fixture.componentInstance.status.setValue('all');
    fixture.componentInstance.search.setValue(' que ');
    fixture.componentInstance.applyFilters();
    expect(api.list).toHaveBeenCalledWith(jasmine.objectContaining({ status: 'all', search: 'que', page: 1 }));
  });
});

describe('RecipeDetailComponent', () => {
  function setup(value: Recipe, compact = false) {
    const api = jasmine.createSpyObj<RecipesApiService>('api', ['get']);
    api.get.and.returnValue(of(value));
    const breakpoints = jasmine.createSpyObj<BreakpointObserver>('breakpoints', ['observe']);
    breakpoints.observe.and.callFake(() => new BehaviorSubject({ matches: compact, breakpoints: {} }));
    TestBed.configureTestingModule({ imports: [RecipeDetailComponent], providers: [...provideTestTranslations(), provideRouter([]),
      { provide: RecipesApiService, useValue: api }, { provide: BreakpointObserver, useValue: breakpoints },
      { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: 'recipe-1' }) } } }] });
    const fixture = TestBed.createComponent(RecipeDetailComponent);
    fixture.detectChanges();
    return fixture;
  }

  it('shows data and ingredients', () => {
    const fixture = setup(recipe);
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Queso');
    expect(fixture.nativeElement.querySelector('[data-testid="detail-yield"]').textContent).toContain('24 u');
    expect(fixture.nativeElement.querySelectorAll('[data-testid="ingredient-row"]').length).toBe(1);
    expect(fixture.nativeElement.querySelector('[data-testid="product-warning"]')).toBeNull();
  });

  it('below 957 px shows label|value rows and one card per ingredient instead of a table', () => {
    const fixture = setup(recipe, true);
    const root = fixture.nativeElement as HTMLElement;
    expect(COMPACT_QUERY).toBe('(max-width: 956.98px)');
    const rows = Array.from(root.querySelectorAll('[data-testid="recipe-info"] .recipe-row')).map(row => row.textContent.trim());
    expect(rows.length).toBe(5);
    expect(rows[0]).toContain('Estado');
    expect(rows[1]).toContain('Cuñapé a granel');
    expect(rows[2]).toContain('24 u');
    expect(root.querySelector('[data-testid="ingredient-table"]')).toBeNull();
    const cards = root.querySelectorAll('[data-testid="ingredient-card"]');
    expect(cards.length).toBe(1);
    const card = cards[0].textContent ?? '';
    expect(card).toContain('Producto');
    expect(card).toContain('Queso');
    expect(card).toContain('Cantidad');
    expect(card).toContain('1.5 kg');
  });

  it('warns when a product is inactive', () => {
    const fixture = setup({ ...recipe, ingredients: [{ ...recipe.ingredients[0], productActive: false }] });
    expect(fixture.nativeElement.querySelector('[data-testid="product-warning"]')).not.toBeNull();
  });
});

describe('RecipeFormComponent', () => {
  let api: jasmine.SpyObj<RecipesApiService>;
  let products: jasmine.SpyObj<ProductsApiService>;
  function create(id: string | null = null) {
    TestBed.configureTestingModule({ imports: [RecipeFormComponent], providers: [...provideTestTranslations(), provideRouter([]),
      { provide: RecipesApiService, useValue: api }, { provide: ProductsApiService, useValue: products },
      { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap(id ? { id } : {}) } } }] });
    const fixture = TestBed.createComponent(RecipeFormComponent);
    fixture.detectChanges();
    return fixture;
  }
  beforeEach(() => {
    api = jasmine.createSpyObj<RecipesApiService>('api', ['get', 'create', 'update']);
    products = jasmine.createSpyObj<ProductsApiService>('products', ['list']);
    products.list.and.returnValue(of({ count: 1, next: null, previous: null, results: [product('p-1', 'Queso', 'u-2', 'kg')] }));
  });

  function fill(component: RecipeFormComponent): void {
    component.form.controls.name.setValue('Queso');
    component.form.controls.result.setValue({ id: 'p-res', name: 'Cuñapé', unitId: 'u-1', unitAbbreviation: 'u' });
    component.form.controls.yieldQuantity.setValue('24');
    component.lines.at(0).controls.product.setValue({ id: 'p-1', name: 'Queso', unitId: 'u-2', unitAbbreviation: 'kg' });
    component.lines.at(0).controls.quantity.setValue('1.5');
  }

  it('starts with one empty ingredient line and blocks an invalid submit', () => {
    const fixture = create();
    const component = fixture.componentInstance;
    expect(component.lines.length).toBe(1);
    component.save();
    fixture.detectChanges();
    expect(api.create).not.toHaveBeenCalled();
    expect(fixture.nativeElement.querySelector('[data-testid="name-error"]')).not.toBeNull();
  });

  it('sends the ingredient unit derived from its product and navigates to the detail', () => {
    api.create.and.returnValue(of(recipe));
    const fixture = create();
    const navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
    fill(fixture.componentInstance);
    fixture.componentInstance.save();
    expect(api.create).toHaveBeenCalledWith({ name: 'Queso', resultProductId: 'p-res', yieldQuantity: '24',
      ingredients: [{ productId: 'p-1', unitId: 'u-2', quantity: '1.5' }] });
    expect(navigate).toHaveBeenCalledWith(['/pocketbiz/production/recipes', 'recipe-1']);
  });

  it('blocks repeated ingredients and the result used as ingredient', () => {
    const fixture = create();
    const component = fixture.componentInstance;
    fill(component);
    component.addLine({ id: 'p-1', name: 'Queso', unitId: 'u-2', unitAbbreviation: 'kg' }, '1');
    component.save();
    expect(component.isDuplicate(1)).toBeTrue();
    expect(api.create).not.toHaveBeenCalled();
    component.removeLine(1);
    component.lines.at(0).controls.product.setValue({ id: 'p-res', name: 'Cuñapé', unitId: 'u-1', unitAbbreviation: 'u' });
    component.save();
    expect(api.create).not.toHaveBeenCalled();
  });

  it('explains why the result product cannot be an ingredient (REV-02)', () => {
    const fixture = create();
    const component = fixture.componentInstance;
    fill(component);
    component.lines.at(0).controls.product.setValue({ id: 'p-res', name: 'Cuñapé', unitId: 'u-1', unitAbbreviation: 'u' });
    component.save();
    fixture.detectChanges();
    expect(api.create).not.toHaveBeenCalled();
    expect(fixture.nativeElement.querySelector('[data-testid="result-ingredient-error"]')).not.toBeNull();
  });

  it('warns in the form when a saved product is inactive (REV-03)', () => {
    api.get.and.returnValue(of({ ...recipe, ingredients: [{ ...recipe.ingredients[0], productActive: false }] }));
    const fixture = create('recipe-1');
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[data-testid="product-warning"]')).not.toBeNull();
  });

  it('keeps what was typed and shows server errors by field and line', () => {
    api.create.and.returnValue(throwError(() => new RecipeApiError('Revisa', 400,
      { name: 'Duplicada', lines: { 0: { quantity: 'Sin fracciones' } } })));
    const fixture = create();
    fill(fixture.componentInstance);
    fixture.componentInstance.save();
    fixture.detectChanges();
    expect(fixture.componentInstance.form.controls.name.value).toBe('Queso');
    expect(fixture.nativeElement.querySelector('[data-testid="name-error"]').textContent).toContain('Duplicada');
    expect(fixture.nativeElement.querySelector('[data-testid="quantity-error"]').textContent).toContain('Sin fracciones');
    expect(fixture.nativeElement.querySelector('[data-testid="form-error"]').textContent).toContain('Revisa');
  });

  it('loads a recipe for editing and updates it with PUT', () => {
    api.get.and.returnValue(of(recipe));
    api.update.and.returnValue(of(recipe));
    const fixture = create('recipe-1');
    spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
    const component = fixture.componentInstance;
    expect(component.form.controls.yieldQuantity.value).toBe('24');
    expect(component.lines.at(0).controls.quantity.value).toBe('1.5');
    expect(component.hasUnsavedChanges()).toBeFalse();
    component.save();
    expect(api.update).toHaveBeenCalledWith('recipe-1', jasmine.objectContaining({ resultProductId: 'p-res' }));
  });
});
