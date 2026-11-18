import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { ClassificationHintComponent } from './classification-hint.component';

describe('ClassificationHintComponent', () => {
  function render(code: string | null) {
    TestBed.configureTestingModule({ imports: [ClassificationHintComponent], providers: [...provideTestTranslations(), provideRouter([])] });
    const fixture = TestBed.createComponent(ClassificationHintComponent);
    fixture.componentRef.setInput('code', code);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  it('links to the Egresos tab for classification error codes (UI-03)', () => {
    for (const code of ['classification_not_configured', 'classification_invalid']) {
      TestBed.resetTestingModule();
      const link = render(code).querySelector('[data-testid="classification-hint"]') as HTMLAnchorElement;
      expect(link).not.toBeNull();
      expect(link.getAttribute('href')).toContain('tab=expenses');
    }
  });

  it('emits followed when the link is pressed (F-01)', () => {
    TestBed.configureTestingModule({ imports: [ClassificationHintComponent], providers: [...provideTestTranslations(), provideRouter([])] });
    const fixture = TestBed.createComponent(ClassificationHintComponent);
    fixture.componentRef.setInput('code', 'classification_invalid');
    let followed = 0;
    fixture.componentInstance.followed.subscribe(() => followed++);
    fixture.detectChanges();
    (fixture.nativeElement.querySelector('a') as HTMLAnchorElement).click();
    expect(followed).toBe(1);
  });

  it('shows nothing for other codes', () => {
    expect(render('already_voided').querySelector('a')).toBeNull();
    TestBed.resetTestingModule();
    expect(render(null).querySelector('a')).toBeNull();
  });
});
