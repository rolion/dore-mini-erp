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
  ingredients: [{ product_id: 'p-1', product_name: 'Queso', unit_id: 'u-2', unit_abbreviation: 'kg', quantity_per_preparation: '1.5000', expected_quantity: '7.5000', actual_quantity: null }],
  created_at: '2026-11-26T12:00:00Z', started_at: null, actual_output: null, entered_at: null, lot: null, cost_total: null,
  release: null, released_at: null, released_by: null, packing: null,
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

  it('refrigerates with the real consumption and maps shortages from a 409', () => {
    const input = { enteredAt: '2026-11-26T15:00:00.000Z', actualOutput: '118', ingredients: [{ productId: 'p-1', actualQuantity: '7' }] };
    api.refrigerate('order-1', input).subscribe(order => {
      expect(order.status).toBe('refrigerating');
      expect(order.lot?.code).toBe('L-20261126-0001');
      expect(order.ingredients[0].actualQuantity).toBe('7.0000');
      expect(order.actualOutput).toBe('118.0000');
    });
    const ok = http.expectOne('/api/production-orders/order-1/refrigerate/');
    expect(ok.request.method).toBe('POST');
    expect(ok.request.body).toEqual({ entered_at: input.enteredAt, actual_output: '118', ingredients: [{ product_id: 'p-1', actual_quantity: '7' }] });
    ok.flush({
      ...orderDto, status: 'refrigerating', actual_output: '118.0000', entered_at: input.enteredAt, lot: { id: 'lot-1', code: 'L-20261126-0001' },
      cost_total: null, ingredients: [{ ...orderDto.ingredients[0], actual_quantity: '7.0000' }],
    });
    let caught: OrderApiError | undefined;
    api.refrigerate('order-1', input).subscribe({ error: (error: OrderApiError) => caught = error });
    http.expectOne('/api/production-orders/order-1/refrigerate/').flush(
      { detail: 'x', code: 'insufficient_stock', shortages: [{ product_id: 'p-1', product_name: 'Queso', unit_abbreviation: 'kg', requested: '7.0000', available: '5.0000', missing: '2.0000' }] },
      { status: 409, statusText: 'Conflict' });
    expect(caught?.status).toBe(409);
    expect(caught?.fields.code).toBe('insufficient_stock');
    expect(caught?.shortages).toEqual([{ productId: 'p-1', productName: 'Queso', unitAbbreviation: 'kg', requested: '7.0000', available: '5.0000', missing: '2.0000' }]);
  });

  it('releases the lot and maps the release data and the too-early rejection', () => {  // AC-02, AC-03, API-01..03
    api.release('order-1').subscribe(order => {
      expect(order.status).toBe('ready_to_pack');
      expect(order.releasedBy).toBe('Ana');
      expect(order.release).toEqual({ minHours: 12, releasableFrom: '2026-11-27T20:00:00Z', canRelease: false });
    });
    const ok = http.expectOne('/api/production-orders/order-1/release/');
    expect(ok.request.method).toBe('POST');
    ok.flush({ ...orderDto, status: 'ready_to_pack', released_at: '2026-11-27T20:05:00Z', released_by: 'Ana',
      release: { min_hours: 12, releasable_from: '2026-11-27T20:00:00Z', can_release: false } });
    let caught: OrderApiError | undefined;
    api.release('order-1').subscribe({ error: (error: OrderApiError) => caught = error });
    http.expectOne('/api/production-orders/order-1/release/').flush(
      { detail: 'x', code: 'release_too_early', releasable_from: '2026-11-27T20:00:00+00:00', min_hours: 12 }, { status: 409, statusText: 'Conflict' });
    expect(caught?.fields.code).toBe('release_too_early');
    expect(caught?.fields.releasableFrom).toBe('2026-11-27T20:00:00+00:00');
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

  it('keeps per-line ingredient errors aligned with the rows', () => {
    let failure: OrderApiError | undefined;
    api.refrigerate('order-1', { enteredAt: '2026-11-26T15:00:00.000Z', actualOutput: '118', ingredients: [] })
      .subscribe({ error: (error: OrderApiError) => failure = error });
    http.expectOne('/api/production-orders/order-1/refrigerate/').flush(
      { ingredients: [{}, { actual_quantity: ['El ingrediente no controla stock.'] }] }, { status: 400, statusText: 'Bad Request' });
    expect(failure?.fields.ingredientLines).toEqual([undefined, 'El ingrediente no controla stock.']);
    expect(failure?.fields.ingredients).toBeUndefined();
  });

  it('reports a conflict on a repeated start with the server detail', () => {
    let failure: OrderApiError | undefined;
    api.start('order-1').subscribe({ error: (error: OrderApiError) => failure = error });
    http.expectOne('/api/production-orders/order-1/start/').flush({ detail: 'La orden ya fue iniciada.' }, { status: 409, statusText: 'Conflict' });
    expect(failure?.message).toBe('La orden ya fue iniciada.');
  });

  it('packs with a snake_case body and maps the packing, the history and the shortages', () => {  // AC-01, AC-02, AC-04, API-01, API-02
    api.pack('order-1', { requestId: 'req-1', packs: 6, packProductId: 'p-pack', bagProductId: 'p-bag', bagPerPack: 0.17, labelProductId: 'p-label' }).subscribe(order => {
      expect(order.packing?.bulkAvailable).toBe('82.0000');
      expect(order.packing?.packings[0]).toEqual(jasmine.objectContaining({
        number: 1, packs: 6, bulkQuantity: '36.0000', costTotal: null,
        packProduct: { id: 'p-pack', name: 'Pack x6' }, labelProduct: { id: 'p-label', name: 'Etiqueta' }, labelsQuantity: '6.0000', lot: { id: 'lot-1', code: 'L-1' } }));
    });
    const ok = http.expectOne('/api/production-orders/order-1/pack/');
    expect(ok.request.method).toBe('POST');
    expect(ok.request.body).toEqual({ request_id: 'req-1', packs: 6, pack_product_id: 'p-pack', bag_product_id: 'p-bag', bag_per_pack: 0.17, label_product_id: 'p-label' });
    ok.flush({ ...orderDto, status: 'ready_to_pack', packing: {
      units_per_pack: 6, suggested_bag_per_pack: '0.1700', labels_per_pack: 1, bulk_available: '82.0000', bulk_unit_abbreviation: 'u',
      packings: [{ id: 'k-1', number: 1, packs: 6, pack_product: { id: 'p-pack', name: 'Pack x6' }, bag_product: { id: 'p-bag', name: 'Bolsa' },
        label_product: { id: 'p-label', name: 'Etiqueta' }, bulk_quantity: '36.0000', bags_quantity: '1.0200', bag_per_pack: '0.1700', labels_quantity: '6.0000', lot: { id: 'lot-1', code: 'L-1' }, cost_total: null, unit_cost: null,
        created_at: '2026-11-27T11:00:00Z', created_by: 'Ana' }] } });

    let caught: OrderApiError | undefined;
    api.pack('order-1', { requestId: 'req-2', packs: 20, packProductId: 'p-pack', bagProductId: 'p-bag', bagPerPack: 1, labelProductId: null }).subscribe({ error: (error: OrderApiError) => caught = error });
    http.expectOne('/api/production-orders/order-1/pack/').flush(
      { detail: 'Faltan', code: 'insufficient_stock', shortages: [{ product_id: 'p-bag', product_name: 'Bolsa', unit_abbreviation: 'u', requested: '20.0000', available: '2.0000', missing: '18.0000' }] },
      { status: 409, statusText: 'Conflict' });
    expect(caught?.fields.code).toBe('insufficient_stock');
    expect(caught?.shortages[0]).toEqual(jasmine.objectContaining({ productName: 'Bolsa', missing: '18.0000' }));
  });
});
