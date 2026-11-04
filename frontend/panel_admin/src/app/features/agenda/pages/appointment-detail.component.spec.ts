import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { Appointment } from '../models/appointment';
import { AppointmentDetailComponent } from './appointment-detail.component';
import { provideTestTranslations } from '../../../core/i18n/testing';

function appointment(overrides: Partial<Appointment> = {}): Appointment {
  return {
    id: 'a1', professional_id: 'p', professional_name: 'Dra. Ana', customer_id: 'c', customer_name: 'Rosa Pérez', service_id: 's',
    service_name: 'Limpieza', starts: '2030-01-07T09:00:00-04:00', ends: '2030-01-07T09:30:00-04:00',
    duration_minutes: 30, notes: '', status: 'scheduled', timezone: 'America/La_Paz',
    allowed_actions: ['confirm', 'reschedule', 'cancel'], history: [{ id: 1, kind: 'created', author_id: 7, author_name: 'recepcion', created_at: '2030-01-01T08:00:00-04:00', reason: '', previous_starts: null, previous_ends: null }], ...overrides,
  };
}

describe('AppointmentDetailComponent', () => {
  let http: HttpTestingController;

  function create() {
    TestBed.configureTestingModule({
      providers: [
        ...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting(), provideRouter([]),
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: new Map([['id', 'a1']]) } } },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(AppointmentDetailComponent);
    fixture.detectChanges();
    http.expectOne(req => req.url.endsWith('/agenda/appointments/a1/')).flush(appointment());
    fixture.detectChanges();
    return fixture;
  }

  afterEach(() => http.verify());

  it('shows only the actions the server allows', () => {
    const fixture = create();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Rosa Pérez');
    expect(text).toContain('Dra. Ana');
    expect(text).toContain('recepcion');
    expect(text).toContain('Confirmar');
    expect(text).toContain('Reprogramar');
    expect(text).not.toContain('Marcar atendida');
  });

  it('requires a reason to cancel and keeps it when the server answers with a conflict', () => {
    const fixture = create();
    const component = fixture.componentInstance;
    const dialog = document.createElement('dialog');
    dialog.showModal = () => undefined;
    dialog.close = () => undefined;
    component.open(dialog, 'cancel');
    expect(component.canSubmit).toBeFalse();
    component.form.controls.reason.setValue('  Paciente avisó ');
    expect(component.canSubmit).toBeTrue();
    component.submit(dialog);
    const request = http.expectOne(req => req.url.endsWith('/agenda/appointments/a1/cancel/'));
    expect(request.request.body).toEqual({ reason: '  Paciente avisó ' });
    request.flush({ detail: 'La cita ya fue cancelada.', code: 'invalid_transition' }, { status: 409, statusText: 'Conflict' });
    http.expectOne(req => req.url.endsWith('/agenda/appointments/a1/')).flush(appointment({ status: 'cancelled', allowed_actions: [] }));
    expect(component.dialogError).toBe('La cita no admite esta acción en su estado actual.');
    expect(component.form.controls.reason.value).toBe('  Paciente avisó ');
    expect(component.appointment?.status).toBe('cancelled');
  });

  it('updates the appointment and reports success after confirming', () => {
    const fixture = create();
    const component = fixture.componentInstance;
    const dialog = document.createElement('dialog');
    dialog.showModal = () => undefined;
    dialog.close = () => undefined;
    component.open(dialog, 'confirm');
    component.submit(dialog);
    http.expectOne(req => req.url.endsWith('/agenda/appointments/a1/confirm/'))
      .flush(appointment({ status: 'confirmed', allowed_actions: ['reschedule', 'cancel'] }));
    expect(component.success).toBe('Cita confirmada.');
    expect(component.appointment?.status).toBe('confirmed');
  });
});
