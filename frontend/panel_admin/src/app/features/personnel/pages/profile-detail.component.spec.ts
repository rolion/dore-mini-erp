import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { Profile } from '../models/profile';
import { PersonnelApiService } from '../services/personnel-api.service';
import { ProfileDetailComponent } from './profile-detail.component';

describe('ProfileDetailComponent', () => {
  it('shows inactive profile, optional data and historic authors (AC-05)', () => {
    const api = jasmine.createSpyObj<PersonnelApiService>('api', ['get', 'users']);
    api.get.and.returnValue(of({ id: 'p', name: 'Ana', active: false, user_id: null, specialties: [],
      created_by: 4, updated_by: 8, created_at: '2026-11-02T10:00:00Z', updated_at: '2026-11-02T11:00:00Z' } as Profile));
    TestBed.configureTestingModule({ imports: [ProfileDetailComponent], providers: [provideRouter([]),
      { provide: PersonnelApiService, useValue: api },
      { provide: ActivatedRoute, useValue: { snapshot: { data: { kind: 'professionals' } }, paramMap: of(convertToParamMap({ id: 'p' })) } },
    ] });
    const fixture = TestBed.createComponent(ProfileDetailComponent);
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Inactivo');
    expect(text).toContain('Sin usuario');
    expect(text).toContain('Sin especialidades');
    expect(text).toContain('Usuario #4');
    expect(text).toContain('Usuario #8');
    expect(api.users).not.toHaveBeenCalled();
  });
});
