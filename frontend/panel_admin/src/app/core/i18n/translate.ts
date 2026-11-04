import { TranslateService } from '@ngx-translate/core';

let translator: TranslateService | null = null;
let fallbackCatalog: Record<string, unknown> | null = null;

/** `LanguageService` registra aquí el traductor para el código que no puede inyectarlo (modelos, funciones puras). */
export function registerTranslator(service: TranslateService): void {
  translator = service;
}

/** Solo pruebas: catálogo usado por `tr` cuando no hay `TranslateService` registrado. */
export function registerFallbackCatalog(catalog: Record<string, unknown>): void {
  fallbackCatalog = catalog;
}

function fromCatalog(key: string, params?: Record<string, unknown>): string {
  let node: unknown = fallbackCatalog;
  for (const part of key.split('.')) {
    node = typeof node === 'object' && node !== null ? (node as Record<string, unknown>)[part] : undefined;
  }
  if (typeof node !== 'string') {
    return key;
  }
  return node.replace(/\{\{\s*(\w+)\s*\}\}/g, (_, name: string) => String(params?.[name] ?? ''));
}

/**
 * Traduce una clave del catálogo en el idioma activo. Para textos que se arman en código
 * (mensajes de error, confirmaciones, etiquetas); en plantillas se usa el pipe `translate`.
 * No evaluar en constantes de módulo: el catálogo se carga al arrancar la aplicación (las
 * etiquetas de módulo usan getters o funciones).
 */
export function tr(key: string, params?: Record<string, unknown>): string {
  if (translator) {
    return String(translator.instant(key, params));
  }
  return fallbackCatalog ? fromCatalog(key, params) : key;
}
