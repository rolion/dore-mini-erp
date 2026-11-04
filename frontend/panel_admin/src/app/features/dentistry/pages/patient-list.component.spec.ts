import { provideTestTranslations } from '../../../core/i18n/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { BehaviorSubject, of, throwError } from 'rxjs';
import { DentistryApiService } from '../services/dentistry-api.service';
import { EMPTY_HISTORY, makePatient } from '../testing/patient-fixtures';
import { PatientListComponent } from './patient-list.component';
describe('PatientListComponent', () => {
  let api: jasmine.SpyObj<DentistryApiService>;
  const params = new BehaviorSubject(convertToParamMap({ search: 'Ana', active: 'false', page: '2' }));
  beforeEach(async () => {
    api = jasmine.createSpyObj<DentistryApiService>('api', ['list']);
    api.list.and.returnValue(of({ ...EMPTY_HISTORY, count: 1, results: [makePatient()] }));
    await TestBed.configureTestingModule({ imports: [PatientListComponent], providers: [...provideTestTranslations(), provideRouter([]),
      { provide: DentistryApiService, useValue: api },
      { provide: ActivatedRoute, useValue: { queryParamMap: params, snapshot: {} } },
    ] }).compileComponents();
  });
  it('restores URL filters and requests server pagination', () => {
    const fixture = TestBed.createComponent(PatientListComponent); fixture.detectChanges();
    expect(api.list).toHaveBeenCalledWith('Ana', 'false', 2);
    expect(fixture.componentInstance.filters).toEqual({ search: 'Ana', active: 'false', page: 2 });
  });
  it('shows a retryable error and never leaves stale patient rows on failure', () => {
    api.list.and.returnValue(throwError(() => new HttpErrorResponse({ status: 500 })));
    const fixture = TestBed.createComponent(PatientListComponent); fixture.detectChanges();
    expect(fixture.componentInstance.rows).toEqual([]);
    expect(fixture.nativeElement.textContent).toContain('Reintentar');
    api.list.and.returnValue(of(EMPTY_HISTORY)); fixture.componentInstance.retry(); fixture.detectChanges();
    expect(fixture.componentInstance.error).toBe(''); expect(fixture.nativeElement.textContent).toContain('No hay pacientes que coincidan');
  });
  it('shows age with a minor badge, updated date, search help and a visible clear button (AC-08, AC-09, AC-10)', () => {
    const birth = new Date(); birth.setFullYear(birth.getFullYear() - 10);
    const iso = `${birth.getFullYear()}-${String(birth.getMonth() + 1).padStart(2, '0')}-${String(birth.getDate()).padStart(2, '0')}`;
    const patient = makePatient(); patient.customer.birth_date = iso;
    api.list.and.returnValue(of({ ...EMPTY_HISTORY, count: 1, results: [patient] }));
    const fixture = TestBed.createComponent(PatientListComponent); fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('10'); expect(text).toContain('Menor'); expect(text).toContain('/11/2026');
    expect(text).toContain('Edad'); expect(text).toContain('Actualizado');
    expect(text).toContain('Se ignoran espacios y guiones');
    expect(fixture.componentInstance.hasFilters).toBeTrue();
    expect(text).toContain('Limpiar filtros');
  });
  it('hides the clear button with default filters and suggests "Todos" when nothing matches (AC-10, AC-11)', () => {
    params.next(convertToParamMap({ search: '', active: 'true', page: '1' }));
    api.list.and.returnValue(of(EMPTY_HISTORY));
    const fixture = TestBed.createComponent(PatientListComponent); fixture.detectChanges();
    expect(fixture.componentInstance.hasFilters).toBeFalse();
    expect(fixture.nativeElement.textContent).not.toContain('Limpiar filtros');
    expect(fixture.nativeElement.textContent).toContain('Aún no hay pacientes. Registra el primero');
    params.next(convertToParamMap({ search: 'zzz', active: 'true', page: '1' })); fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Prueba también con «Todos»');
    params.next(convertToParamMap({ search: 'Ana', active: 'false', page: '2' }));
  });
});
