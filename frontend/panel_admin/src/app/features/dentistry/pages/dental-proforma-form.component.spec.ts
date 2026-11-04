import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { makePatient } from '../testing/patient-fixtures';
import { DentalProformaFormComponent } from './dental-proforma-form.component';

const EMPTY_PAGE = { count: 0, next: null, previous: null, results: [] };
const SERVICE = {
  id: 's1', name: 'Limpieza', code: '', description: '', base_price: '100.00', duration_minutes: 30,
  specialty_id: null, specialty_name: null, active: true, created_at: '', updated_at: '',
};

describe('DentalProformaFormComponent', () => {
  let http: HttpTestingController;

  function create(patientActive = true) {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(), provideHttpClientTesting(), provideRouter([]), ...provideTestTranslations(),
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ patientId: 'c-1' }) } } },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(DentalProformaFormComponent);
    fixture.detectChanges();
    http.expectOne(req => req.url.endsWith('/services/')).flush({ ...EMPTY_PAGE, count: 1, results: [SERVICE] });
    http.expectOne(req => req.url.endsWith('/patients/c-1/')).flush(makePatient({ active: patientActive }));
    fixture.detectChanges();
    return fixture;
  }

  afterEach(() => http.verify());

  it('shows the patient, the dental piece column and previews the total (100 + 150 = 250.00)', () => {
    const fixture = create();
    const component = fixture.componentInstance;
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(component.patientName).toBe('Ana');
    expect(text).toContain('Pieza dental');
    component.lines.at(0).patchValue({ service_id: 's1', quantity: '1', unit_price: '100' });
    component.addLine();
    component.lines.at(1).patchValue({ service_id: 's1', quantity: '1', unit_price: '150' });
    expect(component.total).toBe('250.00');
  });

  it('sends the dental piece of each line to the patient endpoint and no customer id', () => {
    const component = create().componentInstance;
    component.lines.at(0).patchValue({ service_id: 's1', dental_piece: '36' });
    component.pickService(0);
    component.addLine();
    component.lines.at(1).patchValue({ service_id: 's1' });
    component.pickService(1);
    component.submit();
    component.submit();
    const requests = http.match(req => req.method === 'POST');
    expect(requests.length).toBe(1);
    expect(requests[0].request.url).toContain('/dentistry/patients/c-1/proformas/');
    const [first, second] = requests[0].request.body.lines;
    expect(first.dental_piece).toBe('36');
    expect(second.dental_piece).toBe('');
    expect('unit_price' in first).toBeFalse();
    expect('customer_id' in requests[0].request.body).toBeFalse();
    requests[0].flush({ id: 'p1' });
  });

  it('rejects a piece longer than 20 characters before sending', () => {
    const component = create().componentInstance;
    component.lines.at(0).patchValue({ service_id: 's1', unit_price: '5', dental_piece: 'x'.repeat(21) });
    component.submit();
    http.expectNone(req => req.method === 'POST');
    expect(component.lines.at(0).get('dental_piece')?.invalid).toBeTrue();
  });

  it('keeps the data and marks the failing piece on a 400', () => {
    const component = create().componentInstance;
    component.lines.at(0).patchValue({ service_id: 's1', quantity: '1', unit_price: '5', dental_piece: '1' });
    component.submit();
    http.expectOne(req => req.method === 'POST').flush(
      { lines: [{ dental_piece: ['x'] }] }, { status: 400, statusText: 'Bad Request' });
    expect(component.lineErrors[0]['dental_piece']).toContain('20 caracteres');
    expect(component.lines.at(0).get('dental_piece')?.value).toBe('1');
    expect(component.saving).toBeFalse();
  });

  it('blocks saving for an archived patient', () => {
    const fixture = create(false);
    const component = fixture.componentInstance;
    expect(component.readOnly).toBeTrue();
    component.lines.at(0).patchValue({ service_id: 's1', unit_price: '5' });
    component.submit();
    http.expectNone(req => req.method === 'POST');
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('archivado');
  });
});
