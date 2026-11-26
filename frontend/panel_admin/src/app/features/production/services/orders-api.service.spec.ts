import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { OrderApiError, ProductionOrderDto, formatOrderNumber, multiplyQuantity, parsePreparations } from '../models/order';
import { OrdersApiService } from './orders-api.service';

export const orderDto: ProductionOrderDto = {
  id: 'order-1', number: 7, status: 'draft', recipe: { id: 'r-1', name: 'Cuñapé' },
  result_product: { id: 'p-res', name: 'Cuñapé a granel', unit: { id: 'u-1', abbreviation: 'u' } },
  warehouse: { id: 'w-1', name: 'Principal' }, preparations: 5, yield_per_preparation: '24.0000', expected_output: '120.0000',
  ingredients: [{ product_id: 'p-1', product_name: 'Queso', unit_id: 'u-2', unit_abbreviation: 'kg', quantity_per_preparation: '1.5000', expected_quantity: '7.5000' }],
  created_at: '2026-11-26T12:00:00Z', started_at: null,
};

describe('order helpers', () => {
  it('formats the number as OP-0001 and multiplies decimals without float', () => {
    expect(formatOrderNumber(1)).toBe('OP-0001');
    expect(formatOrderNumber(12345)).toBe('OP-12345');
    expect(multiplyQuantity('24.0000', 5)).toBe('120');
    expect(multiplyQuantity('0.1', 3)).toBe('0.3');
    expect(multiplyQuantity('1.5', 5)).toBe('7.5');
    expect(multiplyQuantity('abc', 5)).toBeNull();
  });

  it('accepts only whole numbers from 1 to 99999', () => {
    expect(parsePreparations('5')).toBe(5);
    for (const bad of ['0', '-1', '2.5', 'abc', '', '100000']) expect(parsePreparations(bad)).toBeNull();
  });
});

describe('OrdersApiService', () => {
  let api: OrdersApiService;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting()] });
    api = TestBed.inject(OrdersApiService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('creates with a snake_case body and maps the response', () => {
    api.create({ recipeId: 'r-1', warehouseId: 'w-1', preparations: 5 }).subscribe(order => {
      expect(order.number).toBe(7);
      expect(order.expectedOutput).toBe('120.0000');
      expect(order.resultProduct.unit?.abbreviation).toBe('u');
      expect(order.ingredients[0].expectedQuantity).toBe('7.5000');
      expect(order.startedAt).toBeNull();
    });
    const req = http.expectOne('/api/production-orders/');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ recipe_id: 'r-1', warehouse_id: 'w-1', preparations: 5 });
    req.flush(orderDto);
  });

  it('lists with status and pagination', () => {
    api.list({ status: 'draft', page: 2, pageSize: 20 }).subscribe(page => expect(page.results[0].recipe.name).toBe('Cuñapé'));
    const req = http.expectOne(r => r.url === '/api/production-orders/' && r.params.get('status') === 'draft');
    expect(req.request.params.get('page')).toBe('2');
    expect(req.request.params.get('page_size')).toBe('20');
    req.flush({ count: 1, next: null, previous: null, results: [orderDto] });
  });

  it('gets, updates with PUT, starts and lists warehouses', () => {
    api.get('order-1').subscribe();
    http.expectOne('/api/production-orders/order-1/').flush(orderDto);
    api.update('order-1', { warehouseId: 'w-2', preparations: 3 }).subscribe();
    const put = http.expectOne('/api/production-orders/order-1/');
    expect(put.request.method).toBe('PUT');
    expect(put.request.body).toEqual({ warehouse_id: 'w-2', preparations: 3 });
    put.flush(orderDto);
    api.start('order-1').subscribe(order => expect(order.status).toBe('in_preparation'));
    const start = http.expectOne('/api/production-orders/order-1/start/');
    expect(start.request.method).toBe('POST');
    start.flush({ ...orderDto, status: 'in_preparation', started_at: '2026-11-26T13:00:00Z' });
    api.warehouses().subscribe(items => expect(items).toEqual([{ id: 'w-1', name: 'Principal', isDefault: true }]));
    http.expectOne('/api/production-orders/warehouses/').flush([{ id: 'w-1', name: 'Principal', is_default: true }]);
  });

  it('maps server validation errors by field', () => {
    let failure: OrderApiError | undefined;
    api.create({ recipeId: 'x', warehouseId: 'y', preparations: 0 }).subscribe({ error: (error: OrderApiError) => failure = error });
    http.expectOne('/api/production-orders/').flush(
      { recipe_id: ['Receta no válida.'], warehouse_id: ['Almacén no válido.'], preparations: ['Debe ser mayor que cero.'] },
      { status: 400, statusText: 'Bad Request' });
    expect(failure?.status).toBe(400);
    expect(failure?.fields).toEqual(jasmine.objectContaining({
      recipeId: 'Receta no válida.', warehouseId: 'Almacén no válido.', preparations: 'Debe ser mayor que cero.' }));
  });

  it('reports a conflict on a repeated start with the server detail', () => {
    let failure: OrderApiError | undefined;
    api.start('order-1').subscribe({ error: (error: OrderApiError) => failure = error });
    http.expectOne('/api/production-orders/order-1/start/').flush({ detail: 'La orden ya fue iniciada.' }, { status: 409, statusText: 'Conflict' });
    expect(failure?.message).toBe('La orden ya fue iniciada.');
  });
});
