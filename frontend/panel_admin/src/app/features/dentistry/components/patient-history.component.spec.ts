import { provideTestTranslations } from '../../../core/i18n/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { DentistryApiService } from '../services/dentistry-api.service';
import { PatientHistoryComponent } from './patient-history.component';
describe('PatientHistoryComponent', () => {
  let api: jasmine.SpyObj<DentistryApiService>;
  beforeEach(async () => {
    api = jasmine.createSpyObj<DentistryApiService>('api', ['history']);
    await TestBed.configureTestingModule({ imports: [PatientHistoryComponent], providers: [...provideTestTranslations(), { provide: DentistryApiService, useValue: api }] }).compileComponents();
  });
  it('shows audit author, before/after and server-side pagination', () => {
    api.history.and.returnValue(of({ count: 11, next: '/next', previous: null, results: [{ id: 1, author_id: 1,
      author_name: 'ana', action: 'edit', created_at: '2026-11-02T14:00:00Z', before: { allergies: '' }, after: { allergies: 'Penicilina' } }] }));
    const fixture = TestBed.createComponent(PatientHistoryComponent);
    fixture.componentRef.setInput('patientId', 'c-1'); fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('ana');
    expect(fixture.nativeElement.textContent).toContain('Sin registrar');
    expect(fixture.nativeElement.textContent).toContain('Penicilina');
    expect(fixture.nativeElement.textContent).toContain('Datos editados');
    fixture.componentInstance.move(1); expect(api.history).toHaveBeenCalledWith('c-1', true, 2);
  });
  it('clears audit rows on a permission error and offers retry', () => {
    api.history.and.returnValue(throwError(() => new HttpErrorResponse({ status: 403 })));
    const fixture = TestBed.createComponent(PatientHistoryComponent);
    fixture.componentRef.setInput('patientId', 'c-1'); fixture.detectChanges();
    expect(fixture.componentInstance.rows).toEqual([]);
    expect(fixture.nativeElement.textContent).toContain('No tienes permiso');
    expect(fixture.nativeElement.textContent).toContain('Reintentar');
  });
  it('shows a change even when the saved text equals the empty-state label', () => {
    api.history.and.returnValue(of({ count: 1, next: null, previous: null, results: [{
      id: 1, author_id: 1, author_name: 'ana', action: 'edit', created_at: '2026-11-02T14:00:00Z',
      before: { allergies: '' }, after: { allergies: 'Sin registrar' },
    }] }));
    const fixture = TestBed.createComponent(PatientHistoryComponent);
    fixture.componentRef.setInput('patientId', 'c-1');
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Alergias');
  });
  it('truncates long texts with an expand toggle and never shows raw keys (AC-25)', () => {
    const long = 'x'.repeat(300);
    api.history.and.returnValue(of({ count: 1, next: null, previous: null, results: [{
      id: 7, author_id: 1, author_name: 'ana', action: 'create', created_at: '2026-11-02T14:00:00Z',
      before: { allergies: '', campo_nuevo: 'a' }, after: { allergies: long, campo_nuevo: 'b' },
    }] }));
    const fixture = TestBed.createComponent(PatientHistoryComponent);
    fixture.componentRef.setInput('patientId', 'c-1'); fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    expect(root.textContent).toContain('Perfil creado');
    expect(root.textContent).toContain('Otro dato'); expect(root.textContent).not.toContain('campo_nuevo');
    expect(root.textContent).not.toContain(long);
    const toggle = root.querySelector('button.btn-link') as HTMLButtonElement;
    expect(toggle.textContent).toContain('Mostrar texto completo');
    toggle.click(); fixture.detectChanges();
    expect(root.textContent).toContain(long);
    expect(root.querySelector('button.btn-link')?.textContent).toContain('Mostrar menos');
  });
});
