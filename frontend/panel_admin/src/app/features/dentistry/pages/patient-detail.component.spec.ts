import { HttpErrorResponse } from '@angular/common/http';
import { TestBed, ComponentFixture } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { of, Subject, throwError } from 'rxjs';
import { DentistryApiService } from '../services/dentistry-api.service';
import { PatientDetailComponent } from './patient-detail.component';
import { makePatient, EMPTY_HISTORY } from '../testing/patient-fixtures';
import { Patient } from '../models/patient';

describe('PatientDetailComponent', () => {
  let fixture: ComponentFixture<PatientDetailComponent>;
  let api: jasmine.SpyObj<DentistryApiService>;
  async function setup(patient = makePatient()) {
    api = jasmine.createSpyObj<DentistryApiService>('api', ['get', 'update', 'demographics', 'setActive', 'history']);
    api.get.and.returnValue(of(patient)); api.history.and.returnValue(of(EMPTY_HISTORY));
    await TestBed.configureTestingModule({ imports: [PatientDetailComponent], providers: [provideRouter([]),
      { provide: DentistryApiService, useValue: api },
      { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: 'c-1' }), queryParamMap: convertToParamMap({ search: 'Ana', page: '2' }) } } },
    ] }).compileComponents();
    fixture = TestBed.createComponent(PatientDetailComponent); fixture.detectChanges();
  }
  const root = () => fixture.nativeElement as HTMLElement;
  it('separates profile from clinical fields and hides future capabilities', async () => {
    await setup(makePatient({ allergies: 'Dato clínico privado' }));
    expect(root().textContent).toContain('Ana');
    expect(root().textContent).not.toContain('Dato clínico privado');
    expect(root().textContent).not.toContain('Odontograma');
    fixture.componentInstance.tab = 'clinical'; fixture.detectChanges();
    expect(root().textContent).toContain('Dato clínico privado');
    expect(root().querySelector('textarea')?.placeholder).toBe('No informado');
  });
  it('preserves both forms and displays field errors after a failed save', async () => {
    await setup();
    const component = fixture.componentInstance;
    component.clinicalForm.controls.allergies.setValue('Nuevo'); component.clinicalForm.markAsDirty();
    component.adminForm.controls.responsible_name.setValue('Tutor'); component.adminForm.markAsDirty();
    api.update.and.returnValue(throwError(() => new HttpErrorResponse({ status: 400, error: { allergies: ['Error clínico'] } })));
    component.saveClinical();
    expect(component.clinicalForm.controls.allergies.value).toBe('Nuevo');
    expect(component.adminForm.controls.responsible_name.value).toBe('Tutor');
    expect(component.clinicalErrors['allergies']).toBe('Error clínico');
    expect(component.hasUnsavedChanges()).toBeTrue();
  });
  it('blocks double submit and preserves the independent administrative draft on success', async () => {
    await setup();
    const component = fixture.componentInstance;
    const pending = new Subject<Patient>(); api.update.and.returnValue(pending);
    component.clinicalForm.controls.allergies.setValue('A'); component.clinicalForm.markAsDirty();
    component.adminForm.controls.responsible_name.setValue('Tutor'); component.adminForm.markAsDirty();
    component.saveClinical(); component.saveClinical();
    expect(api.update).toHaveBeenCalledTimes(1);
    pending.next(makePatient({ allergies: 'A' })); pending.complete();
    expect(component.clinicalForm.pristine).toBeTrue();
    expect(component.adminForm.dirty).toBeTrue();
    expect(component.adminForm.controls.responsible_name.value).toBe('Tutor');
  });
  it('validates known minors and future date without sending invalid demographics', async () => {
    await setup();
    const component = fixture.componentInstance;
    component.adminForm.controls.birth_date.setValue('2099-01-01'); component.adminForm.markAsDirty();
    component.saveAdmin(); expect(api.demographics).not.toHaveBeenCalled();
    expect(component.adminForm.hasError('futureBirth')).toBeTrue();
  });
  it('keeps the clinical draft on successful independent administrative save', async () => {
    await setup(); const component = fixture.componentInstance;
    component.clinicalForm.controls.medication.setValue('Borrador'); component.clinicalForm.markAsDirty();
    component.adminForm.controls.birth_date.setValue('2000-01-01'); component.adminForm.markAsDirty();
    api.demographics.and.returnValue(of({ birth_date: '2000-01-01', responsible_name: '', responsible_phone: '' }));
    component.saveAdmin();
    expect(component.adminForm.pristine).toBeTrue(); expect(component.clinicalForm.controls.medication.value).toBe('Borrador');
  });
  it('confirms archive and disables editing, keeping history visible', async () => {
    await setup(); spyOn(window, 'confirm').and.returnValue(true);
    api.setActive.and.returnValue(of(makePatient({ active: false })));
    fixture.componentInstance.toggleActive(); fixture.detectChanges();
    expect(api.setActive).toHaveBeenCalledWith('c-1', false);
    expect(fixture.componentInstance.clinicalForm.disabled).toBeTrue();
    expect(root().textContent).toContain('Su historia se conserva');
    expect(api.history).toHaveBeenCalled();
  });
  it('does not archive with unsaved changes and warns on browser exit', async () => {
    await setup(); const component = fixture.componentInstance;
    component.clinicalForm.markAsDirty(); component.toggleActive();
    expect(api.setActive).not.toHaveBeenCalled();
    const event = { preventDefault: jasmine.createSpy('preventDefault'), returnValue: undefined } as unknown as BeforeUnloadEvent;
    component.beforeUnload(event); expect(event.preventDefault).toHaveBeenCalled();
  });
});
