import { provideTestTranslations } from '../../core/i18n/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router, UrlTree } from '@angular/router';
import { Observable, firstValueFrom, of, throwError } from 'rxjs';
import { clinicalGuard } from './clinical.guard';
import { DentistryApiService } from './services/dentistry-api.service';
describe('clinicalGuard', () => {
  let api: jasmine.SpyObj<DentistryApiService>;
  beforeEach(() => {
    api = jasmine.createSpyObj<DentistryApiService>('api', ['capabilities']);
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideRouter([]), { provide: DentistryApiService, useValue: api }] });
  });
  const run = () => firstValueFrom(TestBed.runInInjectionContext(() => clinicalGuard({} as never, {} as never)) as Observable<boolean | UrlTree>);
  it('checks backend capability before allowing navigation', async () => {
    api.capabilities.and.returnValue(of({ clinical_access: true }));
    expect(await run()).toBeTrue(); expect(api.capabilities).toHaveBeenCalled();
  });
  it('denies explicit false and failed capability requests', async () => {
    for (const result of [of({ clinical_access: false }), throwError(() => new Error('403'))]) {
      api.capabilities.and.returnValue(result);
      expect(TestBed.inject(Router).serializeUrl(await run() as UrlTree)).toBe('/pocketbiz/dentistry/access-denied');
    }
  });
});
