import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { AppLanguage, DEFAULT_LANGUAGE } from './language.config';

/**
 * Idioma activo, compartido entre `LanguageService` y `LanguageUrlSerializer` (el serializer lo
 * lee de forma síncrona para prefijar las URLs; no depende de `TranslateService`).
 */
@Injectable({ providedIn: 'root' })
export class LanguageState {
  private readonly subject = new BehaviorSubject<AppLanguage>(DEFAULT_LANGUAGE);

  readonly active$ = this.subject.asObservable();

  get active(): AppLanguage {
    return this.subject.value;
  }

  set(lang: AppLanguage): void {
    if (lang !== this.subject.value) {
      this.subject.next(lang);
    }
  }
}
