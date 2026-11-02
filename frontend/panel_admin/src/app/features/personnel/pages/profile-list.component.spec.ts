import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { of, throwError } from 'rxjs';
import { PersonnelApiService } from '../services/personnel-api.service';
import { ProfileListComponent } from './profile-list.component';

describe('ProfileListComponent', () => {
  let api: jasmine.SpyObj<PersonnelApiService>;
  beforeEach(() => {
    api = jasmine.createSpyObj<PersonnelApiService>('api', ['list', 'specialties']);
    api.list.and.returnValue(of({ count: 0, next: null, previous: null, results: [] }));
    api.specialties.and.returnValue(of([]));
    TestBed.configureTestingModule({ imports: [ProfileListComponent], providers: [provideRouter([]),
      { provide: PersonnelApiService, useValue: api },
      { provide: ActivatedRoute, useValue: { snapshot: { data: { kind: 'professionals' } } } },
    ] });
  });
  it('defaults to active records and changes server-side specialty filter (AC-04)', () => {
    const fixture = TestBed.createComponent(ProfileListComponent);
    fixture.detectChanges();
    expect(api.list).toHaveBeenCalledWith('professionals', jasmine.objectContaining({ active: 'true', page: 1 }));
    fixture.componentInstance.specialty.setValue('s');
    expect(api.list).toHaveBeenCalledWith('professionals', jasmine.objectContaining({ specialty_id: 's' }));
    fixture.componentInstance.onPage({ offset: 1 });
    expect(api.list).toHaveBeenCalledWith('professionals', jasmine.objectContaining({ page: 2 }));
  });
  it('shows a useful error and can retry (AC-07)', () => {
    api.list.and.returnValue(throwError(() => new HttpErrorResponse({ status: 403 })));
    const fixture = TestBed.createComponent(ProfileListComponent);
    fixture.detectChanges();
    expect(fixture.componentInstance.loading).toBeFalse();
    expect(fixture.nativeElement.querySelector('[role="alert"]').textContent).toContain('permiso');
    api.list.and.returnValue(of({ count: 0, next: null, previous: null, results: [] }));
    fixture.componentInstance.refresh();
    expect(fixture.componentInstance.error).toBe('');
  });
});
