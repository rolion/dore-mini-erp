import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { RecipeApiError, RecipeDto } from '../models/recipe';
import { RecipesApiService } from './recipes-api.service';

export const recipeDto: RecipeDto = {
  id: 'recipe-1', name: 'Queso', result_product: { id: 'p-res', name: 'Cuñapé a granel', active: true, unit: { id: 'u-1', abbreviation: 'u' } },
  yield_quantity: '24.0000',
  ingredients: [{ product_id: 'p-1', product_name: 'Queso', product_active: true, unit_id: 'u-2', unit_abbreviation: 'kg', quantity: '1.5000' }],
  active: true, created_at: '2026-11-26T12:00:00Z', updated_at: '2026-11-26T12:00:00Z',
};

describe('RecipesApiService', () => {
  let api: RecipesApiService;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting()] });
    api = TestBed.inject(RecipesApiService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('sends snake_case bodies with decimal strings and maps the response', () => {
    api.create({ name: ' Queso ', resultProductId: 'p-res', yieldQuantity: '24',
      ingredients: [{ productId: 'p-1', unitId: 'u-2', quantity: '1.5' }] })
      .subscribe(recipe => {
        expect(recipe.yieldQuantity).toBe('24.0000');
        expect(recipe.ingredients[0].unitAbbreviation).toBe('kg');
        expect(recipe.resultProduct.unit?.abbreviation).toBe('u');
      });
    const req = http.expectOne('/api/recipes/');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ name: 'Queso', result_product_id: 'p-res', yield_quantity: '24',
      ingredients: [{ product_id: 'p-1', unit_id: 'u-2', quantity: '1.5' }] });
    req.flush(recipeDto);
  });

  it('lists with status, search and pagination', () => {
    api.list({ status: 'all', search: 'que', page: 2, pageSize: 20 }).subscribe(page => expect(page.results[0].name).toBe('Queso'));
    const req = http.expectOne(r => r.url === '/api/recipes/' && r.params.get('status') === 'all');
    expect(req.request.params.get('q')).toBe('que');
    expect(req.request.params.get('page')).toBe('2');
    req.flush({ count: 1, next: null, previous: null, results: [recipeDto] });
  });

  it('updates with PUT and toggles by action URL', () => {
    api.update('recipe-1', { name: 'Queso', resultProductId: 'p-res', yieldQuantity: '24', ingredients: [] }).subscribe();
    const put = http.expectOne('/api/recipes/recipe-1/');
    expect(put.request.method).toBe('PUT');
    put.flush(recipeDto);
    api.setActive('recipe-1', false).subscribe();
    http.expectOne('/api/recipes/recipe-1/deactivate/').flush({ ...recipeDto, active: false });
    api.setActive('recipe-1', true).subscribe();
    http.expectOne('/api/recipes/recipe-1/activate/').flush(recipeDto);
  });

  it('maps server validation errors by field and by line', () => {
    let failure: RecipeApiError | undefined;
    api.create({ name: '', resultProductId: '', yieldQuantity: '', ingredients: [] }).subscribe({ error: (e: RecipeApiError) => failure = e });
    http.expectOne('/api/recipes/').flush({ name: ['Falta'], yield_quantity: ['Mal'],
      ingredients: [{}, { quantity: ['Sin fracciones'], unit_id: ['Unidad base'] }] }, { status: 400, statusText: 'Bad Request' });
    expect(failure?.status).toBe(400);
    expect(failure?.fields.name).toBe('Falta');
    expect(failure?.fields.yieldQuantity).toBe('Mal');
    expect(failure?.fields.lines[0]).toBeUndefined();
    expect(failure?.fields.lines[1]).toEqual(jasmine.objectContaining({ quantity: 'Sin fracciones', unitId: 'Unidad base' }));
  });

  it('flags an invalid page and turns network errors into a message', () => {
    let failure: RecipeApiError | undefined;
    api.list({ page: 9 }).subscribe({ error: (e: RecipeApiError) => failure = e });
    http.expectOne(r => r.url === '/api/recipes/').flush({ page: ['x'] }, { status: 400, statusText: 'Bad Request' });
    expect(failure?.invalidPage).toBeTrue();
    api.get('x').subscribe({ error: (e: RecipeApiError) => failure = e });
    http.expectOne('/api/recipes/x/').error(new ProgressEvent('error'));
    expect(failure?.status).toBe(0);
    expect(failure?.message).toBeTruthy();
  });
});
