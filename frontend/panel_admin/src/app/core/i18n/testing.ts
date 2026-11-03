import { EnvironmentProviders, Provider, importProvidersFrom, inject, provideEnvironmentInitializer } from '@angular/core';
import { TranslateLoader, TranslateModule, TranslateService, TranslationObject } from '@ngx-translate/core';
import { Observable, of } from 'rxjs';
import es from '../../../assets/i18n/es.json';
import { registerTranslator } from './translate';

class SpanishTestLoader implements TranslateLoader {
  getTranslation(): Observable<TranslationObject> {
    return of(es as TranslationObject);
  }
}

/** Traducciones síncronas en español para las pruebas de componentes. */
export function provideTestTranslations(): (Provider | EnvironmentProviders)[] {
  return [
    importProvidersFrom(
      TranslateModule.forRoot({
        fallbackLang: 'es',
        lang: 'es',
        loader: { provide: TranslateLoader, useClass: SpanishTestLoader },
      })
    ),
    provideEnvironmentInitializer(() => registerTranslator(inject(TranslateService))),
  ];
}
