import { Injectable, inject } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { LocalStorageService } from './storage.service';

export const DEFAULT_LANGUAGE = 'es';

@Injectable({
  providedIn: 'root',
})
export class LanguageService {
  public languages: string[] = ['en', 'es', 'de'];
  public translate = inject(TranslateService);
  private storageService = inject(LocalStorageService);

  constructor() {
    this.translate.addLangs(this.languages);

    // Sin idioma elegido por el usuario, la aplicación arranca en español (no se usa el del navegador).
    const storedLang = this.storageService.get('lang') as string | null;
    this.setLanguage(storedLang && this.languages.includes(storedLang) ? storedLang : DEFAULT_LANGUAGE);
  }

  public setLanguage(lang: string) {
    this.translate.use(lang);
    this.storageService.set('lang', lang);
  }
}
