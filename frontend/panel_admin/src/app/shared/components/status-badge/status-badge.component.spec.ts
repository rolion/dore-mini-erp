import { TestBed } from '@angular/core/testing';
import { StatusBadgeComponent, StatusTone } from './status-badge.component';

describe('StatusBadgeComponent', () => {
  function render(tone: StatusTone, label: string): HTMLElement {
    const fixture = TestBed.createComponent(StatusBadgeComponent);
    fixture.componentRef.setInput('tone', tone);
    fixture.componentRef.setInput('label', label);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  it('muestra siempre texto, icono y fondo tintado (el color no va solo) - AC-13', () => {
    const tones: StatusTone[] = ['success', 'warning', 'danger', 'info', 'muted'];
    for (const tone of tones) {
      const element = render(tone, `Estado ${tone}`);
      expect(element.textContent?.trim()).toBe(`Estado ${tone}`);
      expect(element.querySelector('i.fas')).not.toBeNull();
      const badge = element.querySelector('span.badge') as HTMLElement;
      expect(badge.className).toContain('-subtle');
      expect(badge.className).toContain('-emphasis');
    }
  });

  it('el icono es decorativo para lectores de pantalla', () => {
    expect(render('success', 'Pagado').querySelector('i')?.getAttribute('aria-hidden')).toBe('true');
  });
});
