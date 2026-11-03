import { Component, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NgbDropdown, NgbDropdownItem, NgbDropdownMenu, NgbDropdownToggle } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { LanguageService } from '../../../core/service/language.service';
import { AppLanguage, LanguageOption } from '../../../core/i18n/language.config';

/** Selector de idioma Spa / En / Pr (DDR-habilitar-idiomas-es-en-pt-selector-de-idioma). */
@Component({
  selector: 'app-language-selector',
  templateUrl: './language-selector.component.html',
  styleUrl: './language-selector.component.scss',
  imports: [NgbDropdown, NgbDropdownToggle, NgbDropdownMenu, NgbDropdownItem, TranslatePipe],
})
export class LanguageSelectorComponent {
  private readonly languageService = inject(LanguageService);

  readonly options: readonly LanguageOption[] = this.languageService.options;
  readonly current = toSignal(this.languageService.current$, { initialValue: this.languageService.current });

  get activeOption(): LanguageOption {
    return this.options.find((option) => option.code === this.current()) ?? this.options[0];
  }

  select(code: AppLanguage): void {
    void this.languageService.setLanguage(code);
  }
}
