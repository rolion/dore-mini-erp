import { TranslateService } from '@ngx-translate/core';

let translator: TranslateService | null = null;

/** `LanguageService` registra aquí el traductor para el código que no puede inyectarlo (modelos, funciones puras). */
export function registerTranslator(service: TranslateService): void {
  translator = service;
}

/**
 * Traduce una clave del catálogo en el idioma activo. Para textos que se arman en código
 * (mensajes de error, confirmaciones, etiquetas); en plantillas se usa el pipe `translate`.
 * Evaluar siempre dentro de funciones o métodos, nunca en constantes de módulo (el catálogo se
 * carga al arrancar la aplicación).
 */
export function tr(key: string, params?: Record<string, unknown>): string {
  return translator ? String(translator.instant(key, params)) : key;
}
