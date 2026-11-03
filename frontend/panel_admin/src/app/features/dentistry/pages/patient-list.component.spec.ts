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
    expect(fixture.componentInstance.error).toBe(''); expect(fixture.nativeElement.textContent).toContain('No hay resultados');
  });
});
