import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { AuthService } from '../../../../core/service/auth.service';
import { LandingComponent } from './landing.component';

describe('LandingComponent', () => {
  let fixture: ComponentFixture<LandingComponent>;
  let authenticated: boolean;

  const root = (): HTMLElement => fixture.nativeElement as HTMLElement;
  const byTestId = (id: string): HTMLElement | null =>
    root().querySelector<HTMLElement>(`[data-testid="${id}"]`);
  const text = (): string => root().textContent ?? '';

  async function create(isAuthenticated: boolean): Promise<void> {
    authenticated = isAuthenticated;
    await TestBed.configureTestingModule({
      imports: [LandingComponent],
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: { get isAuthenticated() { return authenticated; } } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(LandingComponent);
    fixture.detectChanges();
  }

  describe('visitante anónimo', () => {
    beforeEach(async () => create(false));

    it('has a single h1 with the slogan (AC-01, AC-11)', () => {
      const h1 = root().querySelectorAll('h1');
      expect(h1.length).toBe(1);
      expect(h1[0].textContent?.trim()).toBe('Tu negocio en el bolsillo');
    });

    it('points every primary CTA to the signup (AC-02)', () => {
      for (const id of ['cta-header', 'cta-hero', 'cta-steps', 'cta-plan-free', 'cta-closing']) {
        const link = byTestId(id) as HTMLAnchorElement;
        expect(link).withContext(id).not.toBeNull();
        expect(link.getAttribute('href')).withContext(id).toBe('/pocketbiz/signup');
        expect(link.textContent?.trim()).withContext(id).toBe('Empezar gratis');
      }
    });

    it('offers the login link to /pocketbiz/login (AC-02)', () => {
      const hrefs = Array.from(root().querySelectorAll('a')).map((a) => a.getAttribute('href'));
      expect(hrefs).toContain('/pocketbiz/login');
    });

    it('shows the free limits note next to the hero CTA (AC-11)', () => {
      expect(byTestId('free-limits-note')?.textContent?.trim()).toBe(
        'Plan gratuito con límites: 1 producto, 1 cliente, 2 ventas y 2 gastos por día.'
      );
    });

    it('always labels the profit as an estimate with its note (AC-11)', () => {
      const card = byTestId('profit-card') as HTMLElement;
      expect(card.textContent).toContain('Ganancia estimada');
      expect(card.textContent).toContain(
        'Ventas − gastos registrados. Es una estimación, no la utilidad contable.'
      );
      // La pregunta "¿La ganancia es real?" del FAQ es contenido de la spec; se excluye.
      const clone = root().cloneNode(true) as HTMLElement;
      clone.querySelector('#preguntas')?.remove();
      expect(clone.textContent ?? '').not.toMatch(/ganancia(?! estimada)/i);
    });

    it('shows the example caption under the phone and a descriptive alt (AC-11, AC-15)', () => {
      expect(text()).toContain('Captura de la aplicación con datos de ejemplo');
      const img = root().querySelector<HTMLImageElement>('.landing-phone img');
      expect(img?.getAttribute('src')).toContain('landing/dashboard-movil-403-positivo.png');
      expect(img?.getAttribute('alt')?.length).toBeGreaterThan(10);
    });

    it('describes the free plan with its limits and CTA (AC-12)', () => {
      const free = byTestId('plan-free') as HTMLElement;
      for (const phrase of [
        'Bs 0',
        '1 producto',
        '1 cliente',
        '2 ventas y 2 gastos por día',
        'Dashboard y reportes de ventas y gastos',
        'Al llegar al límite sigues viendo tus datos y puedes registrar de nuevo al día siguiente',
      ]) {
        expect(free.textContent).withContext(phrase).toContain(phrase);
      }
    });

    it('shows Pro annual by default, switches to monthly and has no purchase button (AC-12)', () => {
      const pro = byTestId('plan-pro') as HTMLElement;
      expect(byTestId('pro-price')?.textContent).toContain('Bs 350');
      expect(byTestId('pro-price')?.textContent).toContain('al año');
      expect(pro.textContent).toContain('(Bs 30 al mes)');
      expect(byTestId('period-annual')?.getAttribute('aria-pressed')).toBe('true');

      (byTestId('period-monthly') as HTMLButtonElement).click();
      fixture.detectChanges();

      expect(byTestId('pro-price')?.textContent).toContain('Bs 30');
      expect(byTestId('pro-price')?.textContent).toContain('al mes');
      expect(byTestId('period-monthly')?.getAttribute('aria-pressed')).toBe('true');
      expect(byTestId('pro-payment-label')?.textContent?.trim()).toBe('Pago disponible próximamente');
      expect(pro.querySelector('a, button')).toBeNull();
      expect(pro.textContent).not.toMatch(/comprar|pagar ahora|contratar/i);
    });

    it('renders the six questions with the first one open (AC-13)', () => {
      const buttons = Array.from(root().querySelectorAll<HTMLButtonElement>('button[ngbAccordionButton]'));
      expect(buttons.length).toBe(6);
      expect(buttons.map((b) => b.textContent?.trim())).toEqual([
        '¿Necesito instalar algo?',
        '¿Emite facturas o lleva inventario?',
        '¿La ganancia es real?',
        '¿Puedo agregar a mi equipo?',
        '¿Qué pasa si olvido mi contraseña?',
        '¿Qué pasa al llegar al límite del plan gratuito?',
      ]);
      expect(buttons[0].getAttribute('aria-expanded')).toBe('true');
      expect(buttons[1].getAttribute('aria-expanded')).toBe('false');
    });

    it('does not include forbidden claims or legal placeholders (AC-14)', () => {
      const content = text();
      for (const forbidden of [/sin tarjeta/i, /prueba gratis/i, /©/, /privacidad/i, /términos/i, /contacto/i, /testimonio/i]) {
        expect(content).withContext(String(forbidden)).not.toMatch(forbidden);
      }
    });

    it('collapses the mobile menu by default and toggles it (AC-16)', () => {
      const toggler = root().querySelector<HTMLButtonElement>('.landing-toggler') as HTMLButtonElement;
      expect(toggler.getAttribute('aria-expanded')).toBe('false');
      toggler.click();
      fixture.detectChanges();
      expect(toggler.getAttribute('aria-expanded')).toBe('true');
    });
  });

  describe('con sesión activa', () => {
    beforeEach(async () => create(true));

    it('changes every primary CTA to "Ir a mi panel" and hides the login links (AC-01, AC-02)', () => {
      for (const id of ['cta-header', 'cta-hero', 'cta-steps', 'cta-plan-free', 'cta-closing']) {
        const link = byTestId(id) as HTMLAnchorElement;
        expect(link.getAttribute('href')).withContext(id).toBe('/pocketbiz/dashboard/main');
        expect(link.textContent?.trim()).withContext(id).toBe('Ir a mi panel');
      }
      const hrefs = Array.from(root().querySelectorAll('a')).map((a) => a.getAttribute('href'));
      expect(hrefs).not.toContain('/pocketbiz/login');
    });
  });
});
