import { provideTestTranslations } from '../../../core/i18n/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { TestBed, ComponentFixture, fakeAsync, tick } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { of, Subject, throwError } from 'rxjs';
import { DentistryApiService } from '../services/dentistry-api.service';
import { PatientDetailComponent } from './patient-detail.component';
import { makePatient, EMPTY_HISTORY } from '../testing/patient-fixtures';
import { Patient } from '../models/patient';

function yearsAgo(years: number): string {
  const date = new Date(); date.setFullYear(date.getFullYear() - years);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

describe('PatientDetailComponent', () => {
  let fixture: ComponentFixture<PatientDetailComponent>;
  let api: jasmine.SpyObj<DentistryApiService>;
  async function setup(patient = makePatient(), query: Record<string, string> = { search: 'Ana', page: '2' }) {
    api = jasmine.createSpyObj<DentistryApiService>('api', ['get', 'update', 'demographics', 'setActive', 'history']);
    api.get.and.returnValue(of(patient)); api.history.and.returnValue(of(EMPTY_HISTORY));
    await TestBed.configureTestingModule({ imports: [PatientDetailComponent], providers: [...provideTestTranslations(), provideRouter([]),
      { provide: DentistryApiService, useValue: api },
      { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: 'c-1' }), queryParamMap: convertToParamMap(query) } } },
    ] }).compileComponents();
    fixture = TestBed.createComponent(PatientDetailComponent); fixture.detectChanges();
  }
  const root = () => fixture.nativeElement as HTMLElement;
  const text = () => root().textContent ?? '';
  const button = (label: string) => Array.from(root().querySelectorAll('button')).find(b => b.textContent?.includes(label));

  it('puts the clinical summary first, hides the UUID and the global edit button (AC-12, AC-13)', async () => {
    await setup(makePatient({ allergies: 'Dato clínico privado' }));
    expect(text()).toContain('Ana'); expect(text()).toContain('Dato clínico privado');
    expect(text()).toContain('Ver cliente');
    expect(text()).not.toContain('ID cliente'); expect(text()).not.toContain('Editar ficha');
    expect(text()).not.toContain('Odontograma');
    expect(root().querySelector('textarea')).toBeNull();
    expect(text().indexOf('Resumen clínico')).toBeLessThan(text().indexOf('Antecedentes médicos'));
    expect(text().indexOf('Antecedentes médicos')).toBeLessThan(text().indexOf('Datos personales'));
    expect(text().indexOf('Datos personales')).toBeLessThan(text().indexOf('Contacto'));
    expect(text().indexOf('Contacto')).toBeLessThan(text().indexOf('Registro de cambios'));
    expect(text()).toContain('Nombre, teléfono y correo se editan en Clientes.');
  });
  it('shows blank clinical fields as "Sin registrar" and never as a negative finding (AC-14, INV-01)', async () => {
    await setup();
    expect(text()).toContain('Sin registrar');
    expect(text()).not.toMatch(/Sin alergias|Ninguna|No informado/);
    const link = Array.from(root().querySelectorAll('button')).find(b => b.textContent?.includes('Registrar') && b.textContent.includes('Alergias'));
    expect(link).toBeDefined(); link?.click(); fixture.detectChanges();
    expect(fixture.componentInstance.editingClinical).toBeTrue();
  });
  it('edits sections independently with example placeholders, status line and counter (AC-16, AC-18, AC-19)', async () => {
    await setup();
    const component = fixture.componentInstance;
    component.editClinical(); fixture.detectChanges();
    expect(root().querySelector('textarea#allergies')?.getAttribute('placeholder')).toBe('Ej.: penicilina, látex');
    expect(root().querySelector('[data-testid="clinical-status"]')?.textContent).toContain('Sin cambios');
    expect((button('Guardar antecedentes') as HTMLButtonElement).disabled).toBeTrue();
    expect(text()).not.toContain('Guardar historial');
    expect(component.editingAdmin).toBeFalse();
    component.clinicalForm.controls.allergies.setValue('Penicilina'); component.clinicalForm.markAsDirty(); fixture.detectChanges();
    expect(root().querySelector('[data-testid="clinical-status"]')?.textContent).toContain('Cambios sin guardar');
    expect(root().querySelector('#allergies-count')?.textContent?.trim()).toBe('');
    component.clinicalForm.controls.allergies.setValue('x'.repeat(3300)); fixture.detectChanges();
    expect(root().querySelector('#allergies-count')?.textContent).toContain('3300 / 4000');
  });
  it('preserves both drafts and shows the failure only in the saved section (AC-17)', async () => {
    await setup();
    const component = fixture.componentInstance;
    component.editClinical(); component.editAdmin();
    component.clinicalForm.controls.allergies.setValue('Nuevo'); component.clinicalForm.markAsDirty();
    component.adminForm.controls.responsible_name.setValue('Tutor'); component.adminForm.markAsDirty();
    api.update.and.returnValue(throwError(() => new HttpErrorResponse({ status: 400, error: { allergies: ['Error clínico'] } })));
    component.saveClinical(); fixture.detectChanges();
    expect(component.clinicalForm.controls.allergies.value).toBe('Nuevo');
    expect(component.adminForm.controls.responsible_name.value).toBe('Tutor');
    expect(component.clinicalErrors['allergies']).toBe('Error clínico');
    expect(component.hasUnsavedChanges()).toBeTrue();
    expect(root().querySelector('[data-testid="clinical-status"]')?.textContent).toContain('No se pudo guardar. Tus cambios siguen aquí.');
    expect(root().querySelector('[data-testid="admin-status"]')?.textContent).not.toContain('No se pudo guardar');
    expect(root().querySelector('.alert-danger')).toBeNull();
    expect(root().querySelector('#allergies')?.getAttribute('aria-invalid')).toBe('true');
    expect(button('Reintentar')).toBeDefined();
  });
  it('reports partial success: one section saved and the other failed (AC-17)', async () => {
    await setup();
    const component = fixture.componentInstance;
    component.editClinical(); component.editAdmin();
    component.clinicalForm.controls.allergies.setValue('A'); component.clinicalForm.markAsDirty();
    component.adminForm.controls.birth_date.setValue('2000-01-01'); component.adminForm.markAsDirty();
    api.update.and.returnValue(of(makePatient({ allergies: 'A' })));
    api.demographics.and.returnValue(throwError(() => new HttpErrorResponse({ status: 500 })));
    component.saveClinical(); component.saveAdmin(); fixture.detectChanges();
    expect(component.clinicalState).toBe('saved'); expect(component.adminState).toBe('error');
    expect(root().querySelector('[data-testid="clinical-status"]')?.textContent).toContain('Guardado ✓');
    expect(root().querySelector('[data-testid="admin-status"]')?.textContent).toContain('No se pudo guardar');
    expect(component.adminForm.controls.birth_date.value).toBe('2000-01-01');
  });
  it('blocks double submit and preserves the independent administrative draft on success', async () => {
    await setup();
    const component = fixture.componentInstance;
    const pending = new Subject<Patient>(); api.update.and.returnValue(pending);
    component.clinicalForm.controls.allergies.setValue('A'); component.clinicalForm.markAsDirty();
    component.adminForm.controls.responsible_name.setValue('Tutor'); component.adminForm.markAsDirty();
    component.saveClinical(); component.saveClinical();
    expect(api.update).toHaveBeenCalledTimes(1);
    expect(component.statusText('clinical')).toBe('Guardando…');
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
  it('explains the minor rule with age, required markers and a missing-responsible notice (AC-22)', async () => {
    const patient = makePatient(); patient.customer.birth_date = yearsAgo(10);
    await setup(patient);
    expect(text()).toContain('Menor · 10 años'); expect(text()).toContain('10 años');
    expect(text()).toContain('Falta el responsable (obligatorio para menores).');
    fixture.componentInstance.editAdmin(); fixture.detectChanges();
    expect(text()).toContain('Menor de 18 años: indica quién es responsable.');
    expect(root().querySelectorAll('#admin-section .text-danger.small').length).toBeGreaterThanOrEqual(2);
    expect(text()).toContain('Obligatorio');
    fixture.componentInstance.adminForm.markAsDirty(); fixture.componentInstance.saveAdmin(); fixture.detectChanges();
    expect(root().querySelector('#responsible-name')?.getAttribute('aria-invalid')).toBe('true');
  });
  it('archives after the dialog confirmation, shows the read-only banner and keeps history readable (AC-15, AC-23)', async () => {
    await setup();
    const confirm = spyOn(fixture.componentInstance, 'confirmStateChange').and.resolveTo(true);
    api.setActive.and.returnValue(of(makePatient({ active: false })));
    await fixture.componentInstance.toggleActive(); fixture.detectChanges();
    expect(confirm).toHaveBeenCalledWith(false);
    expect(api.setActive).toHaveBeenCalledWith('c-1', false);
    expect(fixture.componentInstance.clinicalForm.disabled).toBeTrue();
    expect(text()).toContain('Perfil archivado. Se conserva su historia.');
    expect(text()).toContain('Perfil archivado — solo lectura. Reactiva el perfil para editarlo.');
    const edit = root().querySelector('#clinical-edit-btn') as HTMLButtonElement;
    expect(edit.disabled).toBeTrue(); expect(edit.title).toContain('Reactiva el perfil');
    expect(button('Reactivar perfil')).toBeDefined();
    fixture.componentInstance.historyOpen = true; fixture.detectChanges();
    expect(api.history).toHaveBeenCalled();
  });
  it('does nothing when the archive dialog is cancelled', async () => {
    await setup(); spyOn(fixture.componentInstance, 'confirmStateChange').and.resolveTo(false);
    await fixture.componentInstance.toggleActive();
    expect(api.setActive).not.toHaveBeenCalled();
  });
  it('does not archive with unsaved changes, names the pending section and warns on browser exit', async () => {
    await setup(); const component = fixture.componentInstance;
    const confirm = spyOn(component, 'confirmStateChange');
    component.clinicalForm.markAsDirty(); await component.toggleActive();
    expect(api.setActive).not.toHaveBeenCalled(); expect(confirm).not.toHaveBeenCalled();
    expect(component.error).toContain('Antecedentes clínicos');
    const event = { preventDefault: jasmine.createSpy('preventDefault'), returnValue: undefined } as unknown as BeforeUnloadEvent;
    component.beforeUnload(event); expect(event.preventDefault).toHaveBeenCalled();
  });
  it('moves focus to the first field on edit and back to the edit button on cancel (AC-20)', fakeAsync(async () => {
    await setup(); const component = fixture.componentInstance;
    component.editClinical(); fixture.detectChanges(); tick();
    expect(document.activeElement?.id).toBe('medical_history');
    component.cancelClinical(); fixture.detectChanges(); tick();
    expect(document.activeElement?.id).toBe('clinical-edit-btn');
  }));
  it('announces profile creation and focuses the clinical section (AC-03)', fakeAsync(async () => {
    await setup(makePatient(), { created: 'true' }); tick(); fixture.detectChanges();
    expect(text()).toContain('Paciente creado. Puedes completar los antecedentes ahora o más tarde.');
    expect(document.activeElement?.id).toBe('clinical-section');
  }));
  it('shows the change log as tabs, one list at a time (AC-24)', async () => {
    await setup(); const component = fixture.componentInstance;
    component.historyOpen = true; fixture.detectChanges();
    expect(text()).toContain('Registro de cambios');
    expect(api.history).toHaveBeenCalledWith('c-1', true, 1);
    (Array.from(root().querySelectorAll('.nav-link')).find(b => b.textContent?.includes('Datos personales')) as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(api.history).toHaveBeenCalledWith('c-1', false, 1);
    expect(root().querySelectorAll('app-patient-history').length).toBe(1);
  });
});
