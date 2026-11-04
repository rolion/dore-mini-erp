// Preparación global de pruebas: `tr()` resuelve en español cuando una prueba no provee TranslateService.
import es from './assets/i18n/es.json';
import { registerFallbackCatalog } from './app/core/i18n/translate';

registerFallbackCatalog(es as Record<string, unknown>);
