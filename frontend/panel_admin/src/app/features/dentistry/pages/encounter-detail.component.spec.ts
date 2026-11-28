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
    expect(text(fixture)).toContain('C-000001');
    expect(text(fixture)).toContain('Iniciar atención');
    expect(text(fixture)).toContain('Cita: Confirmada');
    expect(text(fixture)).toContain('Atención: Pendiente');
    expect(text(fixture)).not.toContain('Finalizar atención');
    expect(text(fixture)).not.toContain('Recetas médicas');
  });

  it('shows allergies and medical history in a clinical alert strip above everything else', () => {
    const fixture = create();
    const alert = (fixture.nativeElement as HTMLElement).querySelector('[data-testid="clinical-alert"]');
    expect(alert?.textContent).toContain('Alergias: Penicilina');
    expect(alert?.textContent).toContain('Antecedentes médicos: Asma');
    expect(alert?.getAttribute('role')).toBe('note');
  });

  it('shows no alert strip when nothing is recorded and says "Sin registrar" with a link to the record', () => {
    const base = encounterDetail();
    const fixture = create(encounterDetail({ patient: { ...base.patient, allergies: '', medical_history: '', birth_date: null } }));
    const element = fixture.nativeElement as HTMLElement;
    expect(element.querySelector('[data-testid="clinical-alert"]')).toBeNull();
    expect(text(fixture)).toContain('Sin registrar');
    expect(text(fixture)).not.toContain('Sin dato');
    expect(element.querySelector('a[href="/pocketbiz/dentistry/patients/c1"]')).not.toBeNull();
  });

  it('shows the odontogram version of this encounter and the patient number as secondary text', () => {
    const current = { id: 'ev3', sequence: 3, status: 'confirmed' as const };
    const fixture = create(inProgress({ odontogram: { can_create: false, root: current, current, versions: 1 } }));
    expect(text(fixture)).toContain('Odontograma de esta atención · versión 1');
    expect(text(fixture)).toContain('N.º 3 del paciente');
  });

  it('keeps Cancel as a separate secondary action and Finish as the primary one next to the notes', () => {
    const fixture = create(inProgress());
    const buttons = Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('button'));
    const finish = buttons.find(b => b.textContent?.includes('Finalizar atención'));
    const cancel = buttons.find(b => b.textContent?.includes('Cancelar atención'));
    expect(finish?.classList).toContain('btn-finish');
    expect(cancel?.classList).toContain('btn-outline-danger');
    expect(finish?.classList).toContain('btn-touch');
  });

  it('shows read-only notes as text, with an explicit empty message', () => {
    const done = inProgress({ allowed_actions: [] });
    done.encounter = { ...done.encounter!, status: 'finished', finished_at: '2030-01-07T09:40:00-04:00', finished_by: { id: 1, name: 'ana' } };
    const fixture = create(done);
    expect((fixture.nativeElement as HTMLElement).querySelector('textarea#obs')).toBeNull();
    expect(text(fixture)).toContain('Sin observaciones');
  });

  it('shows the start button disabled with the reason when the appointment cannot be started yet', () => {
    const fixture = create(encounterDetail({ allowed_actions: [] }));
    const button = Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('button')).find(b => b.textContent?.includes('Iniciar atención'));
    expect(button?.disabled).toBeTrue();
    expect(button?.getAttribute('aria-describedby')).toBe('start-hint');
    expect(text(fixture)).toContain('cuando llegue la hora');
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

  it('saves typed observations before finishing so nothing is lost', () => {
    const fixture = create(inProgress());
    const component = fixture.componentInstance;
    component.observations.setValue('Sensibilidad en 16');
    component.confirmFinish();
    const save = http.expectOne(req => req.url.endsWith('/encounters/e1/') && req.method === 'PATCH');
    expect(save.request.body).toEqual({ observations: 'Sensibilidad en 16' });
    save.flush(inProgress({ encounter: { ...inProgress().encounter!, observations: 'Sensibilidad en 16' } }));
    http.expectOne(req => req.url.endsWith('/encounter/finish/')).flush(inProgress({ allowed_actions: [] }));
  });

  it('finishes directly when there is nothing unsaved', () => {
    const fixture = create(inProgress());
    fixture.componentInstance.confirmFinish();
    http.expectOne(req => req.url.endsWith('/encounter/finish/')).flush(inProgress({ allowed_actions: [] }));
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
