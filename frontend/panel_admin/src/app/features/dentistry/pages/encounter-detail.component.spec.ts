import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, provideRouter } from '@angular/router';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { EncounterDetail } from '../models/encounter';
import { encounterDetail, inProgress } from '../testing/encounter-fixtures';
import { EncounterDetailComponent } from './encounter-detail.component';

describe('EncounterDetailComponent', () => {
  let http: HttpTestingController;

  function create(detail: EncounterDetail = encounterDetail()) {
    TestBed.configureTestingModule({
      providers: [
        ...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting(), provideRouter([]),
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: new Map([['appointmentId', 'a1']]) } } },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(EncounterDetailComponent);
    fixture.detectChanges();
    http.expectOne(req => req.url.endsWith('/dentistry/appointments/a1/encounter/')).flush(detail);
    fixture.detectChanges();
    return fixture;
  }

  const text = (fixture: { nativeElement: unknown }) => (fixture.nativeElement as HTMLElement).textContent ?? '';
  afterEach(() => http.verify());

  it('shows the patient summary and only the start action for a pending appointment', () => {
    const fixture = create();
    expect(text(fixture)).toContain('Atención odontológica');
    expect(text(fixture)).toContain('Ana Pérez');
    expect(text(fixture)).toContain('Penicilina');
    expect(text(fixture)).toContain('Iniciar atención');
    expect(text(fixture)).not.toContain('Finalizar atención');
    expect(text(fixture)).not.toContain('Recetas médicas');
  });

  it('runs the whole flow: start, add odontogram, finish', () => {
    const fixture = create();
    const component = fixture.componentInstance;
    component.run('start');
    http.expectOne(req => req.url.endsWith('/appointments/a1/encounter/start/')).flush(inProgress(), { status: 201, statusText: 'Created' });
    fixture.detectChanges();
    expect(text(fixture)).toContain('Atención iniciada.');
    expect(text(fixture)).toContain('Agregar odontograma');
    const navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
    component.addOdontogram();
    http.expectOne(req => req.url.endsWith('/encounters/e1/odontogram/')).flush({ id: 'ev1' }, { status: 201, statusText: 'Created' });
    expect(navigate).toHaveBeenCalledWith(['/pocketbiz/dentistry/patients', 'c1', 'odontogram'], { queryParams: { evaluation: 'ev1', appointment: 'a1' } });
    component.run('finish');
    const done = inProgress({ allowed_actions: [] });
    done.encounter = { ...done.encounter!, status: 'finished', finished_at: '2030-01-07T09:40:00-04:00', finished_by: { id: 1, name: 'ana' } };
    done.appointment.status = 'attended';
    http.expectOne(req => req.url.endsWith('/appointments/a1/encounter/finish/')).flush(done);
    fixture.detectChanges();
    expect(text(fixture)).toContain('Finalizada');
    expect(text(fixture)).not.toContain('Finalizar atención');
  });

  it('does not send a second request while one is in flight', () => {
    const fixture = create();
    fixture.componentInstance.run('start');
    fixture.componentInstance.run('start');
    const requests = http.match(req => req.url.endsWith('/encounter/start/'));
    expect(requests.length).toBe(1);
    requests[0].flush(inProgress());
  });

  it('requires a reason to cancel and sends it trimmed', () => {
    const fixture = create(inProgress());
    const component = fixture.componentInstance;
    expect(component.canSubmitCancel).toBeFalse();
    component.reason.setValue('  Paciente con fiebre ');
    expect(component.canSubmitCancel).toBeTrue();
    component.confirmCancel();
    const request = http.expectOne(req => req.url.endsWith('/encounter/cancel/'));
    expect(request.request.body).toEqual({ reason: 'Paciente con fiebre' });
    const cancelled = inProgress({ allowed_actions: [] });
    cancelled.encounter = { ...cancelled.encounter!, status: 'cancelled', cancelled_at: '2030-01-07T09:20:00-04:00', cancelled_by: { id: 1, name: 'ana' }, cancellation_reason: 'Paciente con fiebre' };
    request.flush(cancelled);
    fixture.detectChanges();
    expect(text(fixture)).toContain('Paciente con fiebre');
    expect(text(fixture)).toContain('Atención y cita canceladas.');
  });

  it('keeps the dialog open and shows the server message on a draft conflict, then reloads', () => {
    const fixture = create(inProgress());
    fixture.componentInstance.run('finish');
    http.expectOne(req => req.url.endsWith('/encounter/finish/')).flush({ detail: 'x', code: 'draft_pending' }, { status: 409, statusText: 'Conflict' });
    http.expectOne(req => req.url.endsWith('/appointments/a1/encounter/')).flush(inProgress());
    fixture.detectChanges();
    expect(text(fixture)).toContain('Confirma o descarta el odontograma en borrador antes de finalizar.');
  });

  it('offers to continue a draft odontogram and only to view a confirmed one', () => {
    const draft = inProgress({ odontogram: { can_create: false, root: { id: 'ev1', sequence: 1, status: 'draft' }, current: { id: 'ev1', sequence: 1, status: 'draft' } } });
    expect(text(create(draft))).toContain('Continuar odontograma');
  });

  it('explains why the appointment cannot be started', () => {
    const fixture = create(encounterDetail({ allowed_actions: [], is_dental: false }));
    expect(text(fixture)).toContain('no tiene perfil odontológico');
  });
});
