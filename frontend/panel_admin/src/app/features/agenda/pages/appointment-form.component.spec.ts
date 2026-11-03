import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { AppointmentFormComponent } from './appointment-form.component';

const EMPTY_PAGE = { count: 0, next: null, previous: null, results: [] };

describe('AppointmentFormComponent', () => {
  let http: HttpTestingController;

  function create() {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(), provideHttpClientTesting(), provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { queryParamMap: convertToParamMap({ professional: 'p1', starts: '2030-01-07T09:00' }) } },
        },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(AppointmentFormComponent);
    fixture.detectChanges();
    http.expectOne(req => req.url.endsWith('/professionals/')).flush(EMPTY_PAGE);
    http.expectOne(req => req.url.endsWith('/services/')).flush(EMPTY_PAGE);
    http.expectOne(req => req.url.endsWith('/customers/')).flush(EMPTY_PAGE);
    return fixture;
  }

  afterEach(() => http.verify());

  function fill(fixture: ReturnType<typeof create>): void {
    fixture.componentInstance.form.patchValue({ customer_id: 'c1', service_id: 's1', professional_id: 'p1', duration_minutes: 30 });
  }

  it('prefills the professional and start from the calendar slot and computes the end', () => {
    const fixture = create();
    const component = fixture.componentInstance;
    expect(component.form.controls.professional_id.value).toBe('p1');
    expect(component.form.controls.starts.value).toBe('2030-01-07T09:00');
    expect(component.endsLabel).toBe('07/01/2030 09:30');
  });

  it('does not send an invalid form and ignores a second submit while saving', () => {
    const fixture = create();
    const component = fixture.componentInstance;
    component.submit();
    http.expectNone(req => req.method === 'POST');
    fill(fixture);
    component.submit();
    component.submit();
    const requests = http.match(req => req.method === 'POST');
    expect(requests.length).toBe(1);
    expect(requests[0].request.body.starts).toBe('2030-01-07T09:00:00-04:00');
    requests[0].flush({ id: 'a1' });
  });

  it('keeps what was typed on a conflict, explains it and refreshes the free slots', () => {
    const fixture = create();
    const component = fixture.componentInstance;
    fill(fixture);
    component.form.controls.notes.setValue('Llegar temprano');
    component.submit();
    http.expectOne(req => req.method === 'POST').flush({ detail: 'El profesional ya tiene una cita en ese horario.' },
      { status: 409, statusText: 'Conflict' });
    const slots = http.expectOne(req => req.url.endsWith('/agenda/appointments/free-slots/'));
    expect(slots.request.params.get('date_from')).toBe('2030-01-07');
    slots.flush({ timezone: 'America/La_Paz', now: '', slots: [{ starts: '2030-01-07T10:30:00-04:00', ends: '2030-01-07T12:00:00-04:00' }] });
    fixture.detectChanges();
    expect(component.conflict).toBeTrue();
    expect(component.saving).toBeFalse();
    expect(component.form.controls.notes.value).toBe('Llegar temprano');
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('ya tiene una cita');
    expect(text).toContain('10:30–12:00');
    component.useSlot(component.slots[0]);
    expect(component.form.controls.starts.value).toBe('2030-01-07T10:30');
  });
});
