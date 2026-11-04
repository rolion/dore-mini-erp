import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter, Router } from '@angular/router';
import { of } from 'rxjs';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { DentalProforma } from '../models/dental-proforma';
import { DentalProformaDetailComponent } from './dental-proforma-detail.component';

const PROFORMA = (status: DentalProforma['status'], actions: DentalProforma['allowed_actions']): DentalProforma => ({
  id: 'p1', number: 'ODO-000001', version: 1, status, customer_id: 'c-1', patient_name: 'Ana', date: '2026-11-04',
  valid_until: null, currency: 'BOB', total: '250.00', notes: '', can_edit_price: true, allowed_actions: actions,
  lines: [{ id: 'l1', service_id: 's1', description: 'Limpieza', quantity: '1.00', unit_price: '250.00', subtotal: '250.00', dental_piece: '18' },
    { id: 'l2', service_id: 's2', description: 'Corona', quantity: '1.00', unit_price: '0.00', subtotal: '0.00', dental_piece: '' }],
  versions: [{ id: 'p1', number: 'ODO-000001', version: 1, status, customer_id: 'c-1', patient_name: 'Ana', date: '2026-11-04',
    valid_until: null, currency: 'BOB', total: '250.00' }],
});

describe('DentalProformaDetailComponent', () => {
  let http: HttpTestingController;

  function create(proforma: DentalProforma) {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([]), ...provideTestTranslations(),
        { provide: ActivatedRoute, useValue: { paramMap: of(convertToParamMap({ proformaId: 'p1' })) } }],
    });
    http = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(DentalProformaDetailComponent);
    fixture.detectChanges();
    http.expectOne(r => r.url.endsWith('/dentistry/proformas/p1/')).flush(proforma);
    fixture.detectChanges();
    return fixture;
  }

  afterEach(() => http.verify());

  it('shows the dental piece per line (or a dash), the status and the draft actions', () => {
    const fixture = create(PROFORMA('draft', ['edit', 'present']));
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Pieza dental');
    expect(text).toContain('18');
    expect(text).toContain('Borrador');
    expect(text).toContain('Presentar');
    expect(text).toContain('Editar');
    expect(text).not.toContain('Nueva versión');
  });

  it('presents with a confirmation dialog, shows the server error and keeps a double click from sending twice', () => {
    const fixture = create(PROFORMA('draft', ['edit', 'present']));
    const component = fixture.componentInstance;
    const dialog = (fixture.nativeElement as HTMLElement).querySelector('dialog') as HTMLDialogElement;
    component.open(dialog);
    component.present(dialog);
    component.present(dialog);
    const requests = http.match(r => r.method === 'POST' && r.url.endsWith('/present/'));
    expect(requests.length).toBe(1);
    requests[0].flush({ lines: ['x'] }, { status: 400, statusText: 'Bad Request' });
    expect(component.dialogError).toContain('línea');
    expect(component.saving).toBeFalse();
    component.present(dialog);
    http.expectOne(r => r.url.endsWith('/present/')).flush(PROFORMA('presented', ['new-version']));
    fixture.detectChanges();
    expect(component.proforma?.status).toBe('presented');
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Nueva versión');
  });

  it('creates a new version and goes to editing the new draft', () => {
    const fixture = create(PROFORMA('presented', ['new-version']));
    const navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
    fixture.componentInstance.newVersion();
    http.expectOne(r => r.url.endsWith('/new-version/')).flush({ ...PROFORMA('draft', ['edit', 'present']), id: 'p2', version: 2 });
    expect(navigate).toHaveBeenCalledWith(['/pocketbiz/dentistry/proformas', 'p2', 'editar']);
  });
});
