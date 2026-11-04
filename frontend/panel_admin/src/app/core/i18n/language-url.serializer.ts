import { Injectable, inject } from '@angular/core';
import { DefaultUrlSerializer, UrlSerializer, UrlTree } from '@angular/router';
import { LanguageState } from './language-state';
import { addLanguagePrefix, languageFromUrl, stripLanguagePrefix } from './language.config';

/**
 * Las rutas del router no llevan idioma: al interpretar una URL se quita el prefijo (`/en`) y se
 * fija el idioma activo; al generar una URL se antepone el idioma activo
 * (ADR-habilitar-idiomas-es-en-pt-url-con-idioma-y-preferencia). Así `app.routes.ts` y los
 * enlaces `/pocketbiz/...` no cambian.
 */
@Injectable()
export class LanguageUrlSerializer extends DefaultUrlSerializer {
  private readonly state = inject(LanguageState);

  override parse(url: string): UrlTree {
    const lang = languageFromUrl(url);
    if (lang !== null) {
      this.state.set(lang);
      return super.parse(stripLanguagePrefix(url));
    }
    return super.parse(url);
  }

  override serialize(tree: UrlTree): string {
    return addLanguagePrefix(super.serialize(tree), this.state.active);
  }
}

export const LANGUAGE_URL_SERIALIZER_PROVIDER = { provide: UrlSerializer, useClass: LanguageUrlSerializer };
