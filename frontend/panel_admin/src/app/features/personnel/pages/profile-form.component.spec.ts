import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { Subject, of } from 'rxjs';
import { Profile } from '../models/profile';
import { PersonnelApiService } from '../services/personnel-api.service';
import { ProfileFormComponent } from './profile-form.component';

describe('ProfileFormComponent', () => {
  let api: jasmine.SpyObj<PersonnelApiService>;
  beforeEach(() => {
    api = jasmine.createSpyObj<PersonnelApiService>('api', ['get', 'save', 'specialties', 'users']);
    api.specialties.and.returnValue(of([]));
    api.users.and.returnValue(of([]));
    TestBed.configureTestingModule({ imports: [ProfileFormComponent], providers: [provideRouter([]),
      { provide: PersonnelApiService, useValue: api },
      { provide: ActivatedRoute, useValue: { snapshot: { data: { kind: 'professionals' } }, paramMap: of(convertToParamMap({})) } },
    ] });
  });
  it('renders optional selectors and saves with only name (AC-01, AC-07)', () => {
    api.save.and.returnValue(of({ id: 'p' } as Profile));
    spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
    const fixture = TestBed.createComponent(ProfileFormComponent);
    fixture.detectChanges();
    const component = fixture.componentInstance;
    component.form.controls.name.setValue(' Ana ');
    component.submit();
    expect(api.save).toHaveBeenCalledWith('professionals', jasmine.objectContaining({ name: 'Ana', user_id: null, specialty_ids: [] }), null);
    expect(fixture.nativeElement.querySelector('label[for="profile-user"]').textContent).toContain('opcional');
  });
  it('rejects whitespace name and invalid email without sending (AC-01)', () => {
    const fixture = TestBed.createComponent(ProfileFormComponent);
    fixture.detectChanges();
    const component = fixture.componentInstance;
    component.form.patchValue({ name: '   ', email: 'invalid' });
    component.submit();
    expect(api.save).not.toHaveBeenCalled();
    expect(component.errorFor('name')).toBeTruthy();
    expect(component.errorFor('email')).toBeTruthy();
  });
  it('prevents double submission and keeps input on a duplicate-user error (AC-07, AC-08)', () => {
    const pending = new Subject<Profile>();
    api.save.and.returnValue(pending);
    const fixture = TestBed.createComponent(ProfileFormComponent);
    fixture.detectChanges();
    const component = fixture.componentInstance;
    component.form.patchValue({ name: 'Ana', user_id: 7 });
    component.submit();
    component.submit();
    expect(api.save).toHaveBeenCalledTimes(1);
    expect(component.saving).toBeTrue();
    pending.error(new HttpErrorResponse({ status: 400, error: { user_id: ['Usuario ya vinculado.'] } }));
    expect(component.saving).toBeFalse();
    expect(component.form.controls.name.value).toBe('Ana');
    expect(component.form.controls.user_id.value).toBe(7);
    expect(component.errorFor('user_id')).toContain('ya vinculado');
  });
});
