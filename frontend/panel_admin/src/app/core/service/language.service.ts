import { Injectable, inject } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { LocalStorageService } from './storage.service';

@Injectable({
  providedIn: 'root',
})
export class LanguageService {
  public languages: string[] = ['en', 'es', 'de'];
  public translate = inject(TranslateService);
  private storageService = inject(LocalStorageService);

  constructor() {
    let browserLang: string;
    this.translate.addLangs(this.languages);

    const storedLang = this.storageService.get('lang');
    if (storedLang) {
      browserLang = storedLang as string;
    } else {
      browserLang = this.translate.getBrowserLang() as string;
    }
    this.translate.use(browserLang.match(/en|es|de/) ? browserLang : 'en');
  }

  public setLanguage(lang: string) {
    this.translate.use(lang);
    this.storageService.set('lang', lang);
  }
}
