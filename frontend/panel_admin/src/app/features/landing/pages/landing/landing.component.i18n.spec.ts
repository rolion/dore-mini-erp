import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { AuthService } from '../../../../core/service/auth.service';
import { LandingComponent } from './landing.component';

describe('LandingComponent languages (AC-06)', () => {
  let fixture: ComponentFixture<LandingComponent>;
  const root = (): HTMLElement => fixture.nativeElement as HTMLElement;
  const text = (): string => root().textContent ?? '';

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LandingComponent],
      providers: [
        provideRouter([]),
        ...provideTestTranslations(),
        { provide: AuthService, useValue: { get isAuthenticated() { return false; } } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(LandingComponent);
    fixture.detectChanges();
  });

  async function useLanguage(lang: string): Promise<void> {
    await TestBed.inject(TranslateService).use(lang).toPromise();
    fixture.detectChanges();
  }

  it('includes the language selector in the top bar', () => {
    expect(root().querySelector('.landing-actions app-language-selector')).not.toBeNull();
  });

  it('renders the landing in English', async () => {
    await useLanguage('en');
    expect(root().querySelector('h1')?.textContent?.trim()).toBe('Your business in your pocket');
    expect(text()).toContain('Do I need to install anything?');
    expect(text()).not.toContain('Tu negocio en el bolsillo');
    expect(root().querySelector('[data-testid="cta-header"]')?.textContent?.trim()).toBe('Start for free');
  });

  it('renders the landing in Portuguese', async () => {
    await useLanguage('pt');
    expect(root().querySelector('h1')?.textContent?.trim()).toBe('Seu negócio no bolso');
    expect(text()).toContain('Preciso instalar algo?');
    expect(root().querySelector('[data-testid="cta-header"]')?.textContent?.trim()).toBe('Começar grátis');
  });
});
