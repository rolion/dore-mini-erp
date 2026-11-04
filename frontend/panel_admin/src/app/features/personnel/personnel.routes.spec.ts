import { provideTestTranslations } from '../../core/i18n/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, RouterStateSnapshot, UrlTree, provideRouter } from '@angular/router';
import { AuthService } from '../../core/service/auth.service';
import { personnelAdminGuard } from './personnel.routes';

describe('Personal admin guard (AC-06)', () => {
  function check(role: string | undefined) {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideRouter([]), { provide: AuthService, useValue: { currentUserValue: { role } } }] });
    return TestBed.runInInjectionContext(() => personnelAdminGuard({} as ActivatedRouteSnapshot, {} as RouterStateSnapshot));
  }
  it('allows the existing admin role', () => expect(check('admin')).toBeTrue());
  it('denies other roles', () => expect(check('reception') instanceof UrlTree).toBeTrue());
  it('denies sessions without a role', () => expect(check(undefined) instanceof UrlTree).toBeTrue());
});
