import { DOCUMENT, Location } from '@angular/common';
import { Injectable, inject } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { firstValueFrom } from 'rxjs';
import { registerTranslator } from '../i18n/translate';
import { LanguageState } from '../i18n/language-state';
import {
  AppLanguage,
  DEFAULT_LANGUAGE,
  LANGUAGE_OPTIONS,
  LanguageOption,
  SUPPORTED_LANGUAGES,
  addLanguagePrefix,
  isSupportedLanguage,
  stripLanguagePrefix,
  resolveLanguage,
  writeStoredLanguage,
} from '../i18n/language.config';

export { DEFAULT_LANGUAGE } from '../i18n/language.config';

@Injectable({
  providedIn: 'root',
})
export class LanguageService {
  readonly languages: readonly AppLanguage[] = SUPPORTED_LANGUAGES;
  readonly options: readonly LanguageOption[] = LANGUAGE_OPTIONS;
  readonly translate = inject(TranslateService);

  private readonly state = inject(LanguageState);
  private readonly document = inject(DOCUMENT);
  private readonly location = inject(Location);
  private readonly fallbackLoaded: Promise<void>;

  constructor() {
    registerTranslator(this.translate);
    this.translate.addLangs([...SUPPORTED_LANGUAGES]);
    this.fallbackLoaded = firstValueFrom(this.translate.setFallbackLang(DEFAULT_LANGUAGE)).then(
      () => undefined,
      () => undefined
    );
    // Cambios de idioma que vienen de la URL (atrás/adelante, enlaces con otro prefijo).
    this.state.active$.subscribe((lang) => this.apply(lang));
  }

  get current(): AppLanguage {
    return this.state.active;
  }

  /** Idioma activo como flujo (para el selector). */
  get current$() {
    return this.state.active$;
  }

  /**
   * Arranque: resuelve el idioma (prefijo de la URL > preferencia > español) y carga su catálogo
   * antes del primer render. No guarda la preferencia (solo la escribe el selector).
   */
  async init(path: string = this.document.location.pathname): Promise<void> {
    const lang = resolveLanguage(path);
    try {
      await this.load(lang);
      this.state.set(lang);
    } catch {
      await this.load(DEFAULT_LANGUAGE).catch(() => undefined);
      this.state.set(DEFAULT_LANGUAGE);
    }
  }

  /** Cambio elegido por la persona: carga el catálogo, guarda la preferencia y actualiza la URL. */
  async setLanguage(lang: string): Promise<void> {
    if (!isSupportedLanguage(lang)) {
      return;
    }
    try {
      await this.load(lang);
    } catch {
      // Catálogo no disponible (EDGE-03): se mantiene el idioma anterior.
      return;
    }
    writeStoredLanguage(lang);
    this.state.set(lang);
    // Mismo recorrido con otro prefijo; sin navegación del router (no se recargan componentes ni guards).
    this.location.replaceState(addLanguagePrefix(stripLanguagePrefix(this.location.path(true)), lang));
  }

  private async load(lang: AppLanguage): Promise<void> {
    await this.fallbackLoaded;
    await firstValueFrom(this.translate.use(lang));
  }

  private apply(lang: AppLanguage): void {
    if (this.translate.getCurrentLang() !== lang) {
      void firstValueFrom(this.translate.use(lang)).catch(() => undefined);
    }
    this.document.documentElement.lang = lang;
  }
}
