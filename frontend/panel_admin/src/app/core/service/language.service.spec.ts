import { Location } from '@angular/common';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { LanguageState } from '../i18n/language-state';
import { LANGUAGE_STORAGE_KEY } from '../i18n/language.config';
import { provideTestTranslations } from '../i18n/testing';
import { LanguageService } from './language.service';

describe('LanguageService', () => {
  beforeEach(() => {
    window.localStorage.removeItem(LANGUAGE_STORAGE_KEY);
    TestBed.configureTestingModule({ providers: [provideRouter([]), ...provideTestTranslations()] });
  });

  afterEach(() => window.localStorage.removeItem(LANGUAGE_STORAGE_KEY));

  it('starts in Spanish without prefix or preference and does not store it', async () => {
    const service = TestBed.inject(LanguageService);
    await service.init('/pocketbiz/login');
    expect(service.current).toBe('es');
    expect(window.localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBeNull();
  });

  it('uses the stored preference when the URL has no prefix', async () => {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, 'pt');
    const service = TestBed.inject(LanguageService);
    await service.init('/pocketbiz/login');
    expect(service.current).toBe('pt');
  });

  it('gives precedence to the URL prefix and does not overwrite the preference', async () => {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, 'pt');
    const service = TestBed.inject(LanguageService);
    await service.init('/en/pocketbiz/login');
    expect(service.current).toBe('en');
    expect(window.localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe('pt');
  });

  it('ignores invalid or legacy stored values', async () => {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, 'de');
    const service = TestBed.inject(LanguageService);
    await service.init('/');
    expect(service.current).toBe('es');
  });

  it('works when the storage is blocked', async () => {
    spyOn(Storage.prototype, 'getItem').and.throwError('blocked');
    spyOn(Storage.prototype, 'setItem').and.throwError('blocked');
    const service = TestBed.inject(LanguageService);
    await service.init('/');
    await service.setLanguage('en');
    expect(service.current).toBe('en');
  });

  it('changes language: stores it, rewrites the URL prefix keeping query and fragment, sets html lang', async () => {
    const service = TestBed.inject(LanguageService);
    const location = TestBed.inject(Location);
    spyOn(location, 'path').and.returnValue('/es/pocketbiz/sales/orders/12?x=1#a');
    const replace = spyOn(location, 'replaceState');
    await service.init('/');
    await service.setLanguage('pt');
    expect(service.current).toBe('pt');
    expect(window.localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe('pt');
    expect(replace).toHaveBeenCalledWith('/pt/pocketbiz/sales/orders/12?x=1#a');
    expect(document.documentElement.lang).toBe('pt');
    expect(TestBed.inject(TranslateService).getCurrentLang()).toBe('pt');
  });

  it('rejects unsupported languages', async () => {
    const service = TestBed.inject(LanguageService);
    await service.init('/');
    await service.setLanguage('fr');
    expect(service.current).toBe('es');
    expect(window.localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBeNull();
  });

  it('follows language changes that come from the URL (back/forward)', async () => {
    const service = TestBed.inject(LanguageService);
    await service.init('/');
    TestBed.inject(LanguageState).set('en');
    expect(service.current).toBe('en');
  });
});
