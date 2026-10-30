import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { BehaviorSubject, of } from 'rxjs';
import { AppModule } from '../../../../core/models/module';
import { ModulesService } from '../../../../core/service/modules.service';
import { HOME_BASE, HOME_WITH_REPORTING, ModuleDisabledComponent } from './module-disabled.component';

const INVENTORY: AppModule = {
  key: 'inventory',
  name: 'Inventario',
  description: '',
  isBase: false,
  enabled: false,
  requires: [],
  optional: [],
  missingRequires: [],
  capabilities: [],
  missingCapabilities: [],
  adoptedAt: null,
  disableBlockers: [],
};

describe('ModuleDisabledComponent', () => {
  const enabled$ = new BehaviorSubject<ReadonlySet<string> | null>(new Set(['catalog']));

  function render(module: string | null) {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        { provide: ModulesService, useValue: { enabledKeys$: enabled$.asObservable(), modules$: of([INVENTORY]) } },
        { provide: ActivatedRoute, useValue: { queryParamMap: of(convertToParamMap(module ? { module } : {})) } },
      ],
    });
    const fixture = TestBed.createComponent(ModuleDisabledComponent);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  const homeLink = (el: HTMLElement) => el.querySelector<HTMLAnchorElement>('a.btn-primary');

  it('shows the title, the module name and a way back (AC-10)', () => {
    const el = render('inventory');
    expect(el.textContent).toContain('Módulo no habilitado');
    expect(el.textContent).toContain('El módulo Inventario no está habilitado para tu empresa.');
    expect(homeLink(el)?.textContent).toContain('Volver al inicio');
  });

  it('works without a module in the URL', () => {
    expect(render(null).textContent).toContain('Este módulo no está habilitado para tu empresa.');
  });

  it('goes back to Catalog when Reports is disabled (UI-04)', () => {
    enabled$.next(new Set(['catalog']));
    expect(homeLink(render(null))?.getAttribute('href')).toBe(HOME_BASE);
  });

  it('goes back to the dashboard when Reports is enabled (UI-04)', () => {
    enabled$.next(new Set(['catalog', 'reporting']));
    expect(homeLink(render(null))?.getAttribute('href')).toBe(HOME_WITH_REPORTING);
  });
});
