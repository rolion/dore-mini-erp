import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { LanguageState } from '../../../core/i18n/language-state';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { LanguageService } from '../../../core/service/language.service';
import { LanguageSelectorComponent } from './language-selector.component';

describe('LanguageSelectorComponent', () => {
  let fixture: ComponentFixture<LanguageSelectorComponent>;
  let setLanguage: jasmine.Spy;
  const root = (): HTMLElement => fixture.nativeElement as HTMLElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LanguageSelectorComponent],
      providers: [provideRouter([]), ...provideTestTranslations()],
    }).compileComponents();
    setLanguage = spyOn(TestBed.inject(LanguageService), 'setLanguage').and.resolveTo();
    fixture = TestBed.createComponent(LanguageSelectorComponent);
    fixture.detectChanges();
  });

  it('shows the short label of the active language and no flag images (AC-01)', () => {
    expect(root().querySelector('.language-label')?.textContent?.trim()).toBe('Spa');
    expect(root().querySelector('img')).toBeNull();
  });

  it('lists Spa, En and Pr with the name of each language in its own language (AC-01)', () => {
    const options = Array.from(root().querySelectorAll('.language-option')).map((b) =>
      (b.textContent ?? '').replace(/\s+/g, ' ').trim()
    );
    expect(options).toEqual(['Spa Español', 'En English', 'Pr Português']);
  });

  it('marks the active option and updates the label when the language changes', () => {
    TestBed.inject(LanguageState).set('pt');
    fixture.detectChanges();
    expect(root().querySelector('.language-label')?.textContent?.trim()).toBe('Pr');
    const active = root().querySelector('.language-option[aria-current="true"]');
    expect(active?.getAttribute('lang')).toBe('pt');
  });

  it('asks the language service to switch when an option is chosen (AC-03)', () => {
    const english = root().querySelector<HTMLButtonElement>('.language-option[lang="en"]') as HTMLButtonElement;
    english.click();
    expect(setLanguage).toHaveBeenCalledOnceWith('en');
  });

  it('has an accessible name for the toggle', () => {
    expect(root().querySelector('.language-toggle')?.getAttribute('aria-label')).toBe('Idioma');
  });
});
