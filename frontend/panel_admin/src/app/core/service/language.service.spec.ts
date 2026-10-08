import { TestBed } from '@angular/core/testing';
import { TranslateService, provideTranslateService } from '@ngx-translate/core';

import { DEFAULT_LANGUAGE, LanguageService } from './language.service';
import { LocalStorageService } from './storage.service';

describe('LanguageService', () => {
  let storage: jasmine.SpyObj<LocalStorageService>;

  function create(storedLang: string | null) {
    storage = jasmine.createSpyObj<LocalStorageService>('LocalStorageService', ['get', 'set']);
    storage.get.and.returnValue(storedLang);
    TestBed.configureTestingModule({
      providers: [provideTranslateService(), { provide: LocalStorageService, useValue: storage }],
    });
    const service = TestBed.inject(LanguageService);
    return { service, translate: TestBed.inject(TranslateService) };
  }

  it('starts in Spanish and stores it when the user has not chosen a language', () => {
    const { translate } = create(null);
    expect(DEFAULT_LANGUAGE).toBe('es');
    expect(translate.getCurrentLang()).toBe('es');
    expect(storage.set).toHaveBeenCalledWith('lang', 'es');
  });

  it('keeps the language chosen by the user', () => {
    const { translate } = create('de');
    expect(translate.getCurrentLang()).toBe('de');
  });

  it('falls back to Spanish when the stored language is not supported', () => {
    const { translate } = create('fr');
    expect(translate.getCurrentLang()).toBe('es');
  });
});
