/** Idiomas soportados (ADR-habilitar-idiomas-es-en-pt-url-con-idioma-y-preferencia). */
export const SUPPORTED_LANGUAGES = ['es', 'en', 'pt'] as const;
export type AppLanguage = (typeof SUPPORTED_LANGUAGES)[number];

export const DEFAULT_LANGUAGE: AppLanguage = 'es';

/** Clave propia en `localStorage`, sin prefijo de tema. */
export const LANGUAGE_STORAGE_KEY = 'pocketbiz.lang';

export interface LanguageOption {
  /** Código de idioma, también prefijo de la URL. */
  readonly code: AppLanguage;
  /** Etiqueta corta visible en el selector. */
  readonly label: string;
  /** Nombre del idioma en su propio idioma. */
  readonly name: string;
}

export const LANGUAGE_OPTIONS: readonly LanguageOption[] = [
  { code: 'es', label: 'Spa', name: 'Español' },
  { code: 'en', label: 'En', name: 'English' },
  { code: 'pt', label: 'Pr', name: 'Português' },
];

export function isSupportedLanguage(value: unknown): value is AppLanguage {
  return typeof value === 'string' && (SUPPORTED_LANGUAGES as readonly string[]).includes(value);
}

const PREFIX_PATTERN = /^\/(es|en|pt)(?=[/?#]|$)/;

/** Idioma del prefijo de una URL (`/en/pocketbiz…` → `en`), o `null` si no lo trae. */
export function languageFromUrl(url: string): AppLanguage | null {
  const match = PREFIX_PATTERN.exec(url);
  return match ? (match[1] as AppLanguage) : null;
}

/** Quita el prefijo de idioma: `/en/a?x=1` → `/a?x=1`, `/en` → `/`. */
export function stripLanguagePrefix(url: string): string {
  const rest = url.replace(PREFIX_PATTERN, '');
  return rest === '' || rest.startsWith('?') || rest.startsWith('#') ? `/${rest}` : rest;
}

/** Antepone el prefijo; `/` → `/en`. Las rutas del servidor (`/api`, `/admin`) no se tocan. */
export function addLanguagePrefix(url: string, lang: AppLanguage): string {
  if (/^\/(api|admin)(?=[/?#]|$)/.test(url)) {
    return url;
  }
  return url === '/' ? `/${lang}` : `/${lang}${url}`;
}

/** Lectura segura de la preferencia: ignora valores inválidos y almacenamiento bloqueado. */
export function readStoredLanguage(): AppLanguage | null {
  try {
    const value = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
    return isSupportedLanguage(value) ? value : null;
  } catch {
    return null;
  }
}

export function writeStoredLanguage(lang: AppLanguage): void {
  try {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, lang);
  } catch {
    // almacenamiento bloqueado: la preferencia no se guarda
  }
}

/** Precedencia: prefijo de la URL > preferencia guardada > español. */
export function resolveLanguage(url: string): AppLanguage {
  return languageFromUrl(url) ?? readStoredLanguage() ?? DEFAULT_LANGUAGE;
}
