import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { ModulesService } from '../../../core/service/modules.service';
import { PatientEncountersComponent } from './patient-encounters.component';

describe('PatientEncountersComponent', () => {
  let http: HttpTestingController;

  function create() {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting(), provideRouter([])] });
    http = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(PatientEncountersComponent);
    fixture.componentRef.setInput('patientId', 'c1');
    fixture.detectChanges();
    return fixture;
  }

  afterEach(() => http.verify());

  it('lists the encounters of the patient with a link to each', () => {
    const fixture = create();
    http.expectOne(req => req.url.endsWith('/dentistry/patients/c1/encounters/')).flush({
      count: 2, next: null, previous: null, results: [
        { id: 'e2', appointment_id: 'a2', status: 'finished', started_at: '2030-02-01T09:00:00-04:00', finished_at: null, professional_name: 'Dra. Rojas', service_name: 'Limpieza', has_odontogram: true },
        { id: 'e1', appointment_id: 'a1', status: 'in_progress', started_at: '2030-01-01T09:00:00-04:00', finished_at: null, professional_name: 'Dra. Rojas', service_name: 'Control', has_odontogram: false },
      ],
    });
    fixture.detectChanges();
    const element = fixture.nativeElement as HTMLElement;
    expect(element.querySelectorAll('li').length).toBe(2);
    expect(element.textContent).toContain('Con odontograma');
    expect(element.querySelector('a[href="/pocketbiz/dentistry/appointments/a2"]')).not.toBeNull();
  });

  it('hides the card and makes no request when Agenda is disabled', () => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting(), provideRouter([])] });
    http = TestBed.inject(HttpTestingController);
    spyOn(TestBed.inject(ModulesService), 'isDisabled').and.callFake(key => key === 'agenda');
    const fixture = TestBed.createComponent(PatientEncountersComponent);
    fixture.componentRef.setInput('patientId', 'c1');
    fixture.detectChanges();
    http.expectNone(req => req.url.includes('/encounters/'));
    expect((fixture.nativeElement as HTMLElement).querySelector('.card')).toBeNull();
  });

  it('shows an empty state', () => {
    const fixture = create();
    http.expectOne(req => req.url.endsWith('/encounters/')).flush({ count: 0, next: null, previous: null, results: [] });
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Este paciente aún no tiene atenciones.');
  });
});
