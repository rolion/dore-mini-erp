import { EnvironmentProviders, Provider, importProvidersFrom, inject, provideEnvironmentInitializer } from '@angular/core';
import { TranslateLoader, TranslateModule, TranslateService, TranslationObject } from '@ngx-translate/core';
import { Observable, of } from 'rxjs';
import en from '../../../assets/i18n/en.json';
import es from '../../../assets/i18n/es.json';
import pt from '../../../assets/i18n/pt.json';
import { AppLanguage } from './language.config';
import { registerFallbackCatalog, registerTranslator, unregisterTranslator } from './translate';

const CATALOGS: Record<string, TranslationObject> = {
  es: es as TranslationObject,
  en: en as TranslationObject,
  pt: pt as TranslationObject,
};

// Las pruebas de funciones puras (que llaman a `tr` sin TestBed) deben ver siempre español, no el idioma que
// dejó la prueba anterior: el traductor global se olvida tras cada prueba y el catálogo `es` responde por defecto.
registerFallbackCatalog(es as Record<string, unknown>);
afterEach(() => unregisterTranslator());

class TestLoader implements TranslateLoader {
  getTranslation(lang: string): Observable<TranslationObject> {
    return of(CATALOGS[lang] ?? CATALOGS['es']);
  }
}

/** Traducciones síncronas para las pruebas de componentes (español por defecto). */
export function provideTestTranslations(lang: AppLanguage = 'es'): (Provider | EnvironmentProviders)[] {
  return [
    importProvidersFrom(
      TranslateModule.forRoot({
        fallbackLang: 'es',
        lang,
        loader: { provide: TranslateLoader, useClass: TestLoader },
      })
    ),
    provideEnvironmentInitializer(() => registerTranslator(inject(TranslateService))),
  ];
}
