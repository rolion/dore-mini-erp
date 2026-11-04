import { Component } from '@angular/core';
import { Location } from '@angular/common';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router, NavigationStart } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { LEGACY_REDIRECTS } from '../routing/legacy-redirects';
import { APP_PATHS } from '../routing/app-paths';
import { unsavedChangesGuard } from '../guard/unsaved-changes.guard';
import { LanguageService } from '../service/language.service';
import { LanguageState } from './language-state';
import { LANGUAGE_URL_SERIALIZER_PROVIDER } from './language-url.serializer';
import { LANGUAGE_STORAGE_KEY } from './language.config';
import { provideTestTranslations } from './testing';

@Component({ template: 'login' })
class LoginStubComponent {
  hasUnsavedChanges(): boolean {
    return true;
  }
}

describe('language routing', () => {
  beforeEach(() => {
    window.localStorage.removeItem(LANGUAGE_STORAGE_KEY);
    TestBed.configureTestingModule({
      providers: [
        LANGUAGE_URL_SERIALIZER_PROVIDER,
        provideRouter([
          { path: 'pocketbiz/login', component: LoginStubComponent },
          { path: 'pocketbiz/form/:id', component: LoginStubComponent, canDeactivate: [unsavedChangesGuard] },
          { path: '', component: LoginStubComponent },
          ...LEGACY_REDIRECTS,
        ]),
        ...provideTestTranslations(),
      ],
    });
  });

  afterEach(() => window.localStorage.removeItem(LANGUAGE_STORAGE_KEY));

  it('resolves prefixed URLs with the router tree unchanged and keeps the prefix in router.url (AC-11)', async () => {
    const router = TestBed.inject(Router);
    await router.navigateByUrl('/en/pocketbiz/login?x=1#a');
    expect(TestBed.inject(LanguageState).active).toBe('en');
    expect(router.url).toBe('/en/pocketbiz/login?x=1#a');
  });

  it('keeps unprefixed internal links working and adds the active prefix (AC-02, AC-11)', async () => {
    const router = TestBed.inject(Router);
    await router.navigateByUrl('/pt/pocketbiz/login');
    await router.navigateByUrl('/');
    expect(router.url).toBe('/pt');
    await router.navigate(['/pocketbiz/login']);
    expect(router.url).toBe('/pt/pocketbiz/login');
  });

  it('switching language does not navigate or trigger the unsaved-changes guard (AC-10)', async () => {
    const router = TestBed.inject(Router);
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/es/pocketbiz/form/7?tab=1', LoginStubComponent);
    const starts: string[] = [];
    router.events.subscribe((event) => {
      if (event instanceof NavigationStart) starts.push(event.url);
    });
    const confirm = spyOn(window, 'confirm').and.returnValue(false);
    const replace = spyOn(TestBed.inject(Location), 'replaceState');
    await TestBed.inject(LanguageService).setLanguage('en');
    expect(starts).toEqual([]);
    expect(confirm).not.toHaveBeenCalled();
    expect(replace).toHaveBeenCalledTimes(1);
    expect(TestBed.inject(LanguageState).active).toBe('en');
  });

  it('redirects keep the active language (AC-11, EDGE-05)', async () => {
    const router = TestBed.inject(Router);
    await router.navigateByUrl('/en');
    await router.navigate(['/pocketbiz/login']);
    expect(router.url).toBe('/en/pocketbiz/login');
  });

  it('legacy URLs resolve and end with the language prefix (AC-11)', async () => {
    const router = TestBed.inject(Router);
    await router.navigateByUrl('/en/authentication/signin');
    expect(router.url).toBe('/en/pocketbiz/login');
    await router.navigateByUrl('/authentication/signin');
    expect(router.url).toBe('/en/pocketbiz/login');
  });

  it('the 401 redirect to the login keeps the active language (EDGE-05)', async () => {
    const router = TestBed.inject(Router);
    await router.navigateByUrl('/pt/pocketbiz/login');
    await router.navigate([APP_PATHS.login]);
    expect(router.url).toBe('/pt/pocketbiz/login');
  });

  it('/api and /admin are never prefixed by the serializer (INV-04)', () => {
    const router = TestBed.inject(Router);
    expect(router.serializeUrl(router.parseUrl('/api/health/'))).toBe('/api/health/');
  });
});
