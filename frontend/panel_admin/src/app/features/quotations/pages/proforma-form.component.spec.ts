import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { ProformaFormComponent } from './proforma-form.component';

const EMPTY_PAGE = { count: 0, next: null, previous: null, results: [] };
const SERVICE = {
  id: 's1', name: 'Limpieza', code: '', description: '', base_price: '100.00', duration_minutes: 30,
  specialty_id: null, specialty_name: null, active: true, created_at: '', updated_at: '',
};

describe('ProformaFormComponent', () => {
  let http: HttpTestingController;

  function create() {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(), provideHttpClientTesting(), provideRouter([]),
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({}) } } },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(ProformaFormComponent);
    fixture.detectChanges();
    http.expectOne(req => req.url.endsWith('/services/')).flush({ ...EMPTY_PAGE, count: 1, results: [SERVICE] });
    http.expectOne(req => req.url.endsWith('/customers/')).flush(EMPTY_PAGE);
    return fixture;
  }

  afterEach(() => http.verify());

  it('previews subtotals and total with two decimals (100 + 150 = 250.00)', () => {
    const component = create().componentInstance;
    component.lines.at(0).patchValue({ service_id: 's1', quantity: '1', unit_price: '100' });
    component.addLine();
    component.lines.at(1).patchValue({ service_id: 's1', quantity: '1', unit_price: '150' });
    expect(component.subtotal(0)).toBe('100.00');
    expect(component.total).toBe('250.00');
    component.removeLine(1);
    expect(component.total).toBe('100.00');
  });

  it('prefills the catalog price when a service is picked and warns about unsaved changes', () => {
    const component = create().componentInstance;
    expect(component.hasUnsavedChanges()).toBeFalse();
    component.lines.at(0).patchValue({ service_id: 's1' });
    component.pickService(0);
    expect(component.lines.at(0).get('unit_price')?.value).toBe('100.00');
    component.addLine();
    expect(component.hasUnsavedChanges()).toBeTrue();
  });

  it('does not send an invalid form, sends the price only when edited and blocks a double submit', () => {
    const component = create().componentInstance;
    component.submit();
    http.expectNone(req => req.method === 'POST');
    component.form.patchValue({ customer_id: 'c1' });
    component.lines.at(0).patchValue({ service_id: 's1' });
    component.pickService(0);
    component.submit();
    component.submit();
    const requests = http.match(req => req.method === 'POST');
    expect(requests.length).toBe(1);
    const line = requests[0].request.body.lines[0];
    expect(line.service_id).toBe('s1');
    expect('unit_price' in line).toBeFalse();
    requests[0].flush({ id: 'p1' });
  });

  it('keeps the data and marks the failing line on a 400', () => {
    const component = create().componentInstance;
    component.form.patchValue({ customer_id: 'c1' });
    component.lines.at(0).patchValue({ service_id: 's1', quantity: '1', unit_price: '5' });
    component.lines.at(0).get('unit_price')?.markAsDirty();
    component.submit();
    const request = http.expectOne(req => req.method === 'POST');
    expect(request.request.body.lines[0].unit_price).toBe('5');
    request.flush({ lines: [{ unit_price: ['Precio inválido.'] }] }, { status: 400, statusText: 'Bad Request' });
    expect(component.lineErrors[0]['unit_price']).toBe('Precio inválido.');
    expect(component.form.controls.customer_id.value).toBe('c1');
    expect(component.saving).toBeFalse();
  });
});
