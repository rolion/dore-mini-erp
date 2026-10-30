import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { BehaviorSubject, of, throwError } from 'rxjs';
import { AppModule } from '../../../../core/models/module';
import { ModulesService } from '../../../../core/service/modules.service';
import { SettingsApiService } from '../../services/settings-api.service';
import { ModuleListComponent } from './module-list.component';

function mod(key: string, extra: Partial<AppModule> = {}): AppModule {
  return {
    key,
    name: key.toUpperCase(),
    description: `desc ${key}`,
    isBase: false,
    enabled: false,
    requires: [],
    optional: [],
    missingRequires: [],
    capabilities: [],
    missingCapabilities: [],
    adoptedAt: null,
    disableBlockers: [],
    ...extra,
  };
}

describe('ModuleListComponent', () => {
  let fixture: ComponentFixture<ModuleListComponent>;
  let service: jasmine.SpyObj<ModulesService>;
  let modal: jasmine.SpyObj<NgbModal>;
  const modules$ = new BehaviorSubject<AppModule[] | null>(null);

  const el = () => fixture.nativeElement as HTMLElement;
  const button = (name: string) =>
    Array.from(el().querySelectorAll<HTMLTableRowElement>('tbody tr'))
      .find((row) => row.textContent?.includes(`desc ${name}`))
      ?.querySelector<HTMLButtonElement>('button') ?? null;

  const setup = (rows: AppModule[]) => {
    modules$.next(rows);
    service.load.and.returnValue(of(rows));
    fixture = TestBed.createComponent(ModuleListComponent);
    fixture.detectChanges();
  };

  beforeEach(async () => {
    service = jasmine.createSpyObj<ModulesService>('ModulesService', ['load']);
    (service as { modules$: unknown }).modules$ = modules$.asObservable();
    modal = jasmine.createSpyObj<NgbModal>('NgbModal', ['open']);
    await TestBed.configureTestingModule({
      imports: [ModuleListComponent],
      providers: [provideRouter([]), { provide: ModulesService, useValue: service }, { provide: NgbModal, useValue: modal }],
    }).compileComponents();
  });

  it('shows base modules without a toggle (AC-02)', () => {
    setup([mod('catalog', { isBase: true, enabled: true })]);
    expect(button('catalog')).toBeNull();
    expect(el().textContent).toContain('Siempre activo');
    expect(el().textContent).toContain('Base');
  });

  it('blocks enabling and names the missing dependencies (AC-03)', () => {
    setup([mod('purchases', { missingRequires: ['Gastos'], requires: [{ key: 'expenses', name: 'Gastos', enabled: false }] })]);
    const enable = button('purchases');
    expect(enable?.disabled).toBeTrue();
    expect(el().textContent).toContain('Requiere habilitar primero: Gastos');
  });

  it('blocks disabling a module required by an enabled one (AC-05)', () => {
    setup([
      mod('sales', { enabled: true }),
      mod('reporting', { enabled: true, requires: [{ key: 'sales', name: 'SALES', enabled: true }] }),
    ]);
    expect(button('sales')?.disabled).toBeTrue();
    expect(el().textContent).toContain('Lo requieren: REPORTING');
    expect(button('reporting')?.disabled).toBeFalse();
  });

  it('opens the confirmation dialog with the module and affected modules (AC-07)', () => {
    const dialog = { module: undefined as unknown, action: '', affected: [] as string[] };
    modal.open.and.returnValue({ componentInstance: dialog, result: Promise.resolve() } as never);
    setup([mod('inventory', { optional: [{ key: 'sales', name: 'Ventas', enabled: true }] })]);
    button('inventory')?.click();
    expect(modal.open).toHaveBeenCalled();
    expect((dialog.module as AppModule).key).toBe('inventory');
    expect(dialog.action).toBe('enable');
    expect(el().textContent).toContain('Ventas (disponible)');
  });

  it('shows a retry when loading fails', () => {
    service.load.and.returnValue(throwError(() => new Error('No se pudieron cargar los módulos.')));
    modules$.next(null);
    fixture = TestBed.createComponent(ModuleListComponent);
    fixture.detectChanges();
    expect(el().textContent).toContain('No se pudieron cargar los módulos.');
    expect(el().textContent).toContain('Reintentar');
  });

  it('offers General and Historial de cambios tabs; the history uses the modules scope (AC-05, AC-09, UI-06)', () => {
    const api = jasmine.createSpyObj<SettingsApiService>('SettingsApiService', ['history']);
    api.history.and.returnValue(of({ count: 0, results: [], settings: [] }));
    TestBed.overrideProvider(SettingsApiService, { useValue: api });
    setup([mod('sales')]);
    expect(el().textContent).toContain('General');
    expect(el().querySelector('table.modules-table')).not.toBeNull();
    Array.from(el().querySelectorAll('button')).find((b) => b.textContent?.trim() === 'Historial de cambios')?.click();
    fixture.detectChanges();
    expect(api.history).toHaveBeenCalledWith('modules', jasmine.objectContaining({ page: 1 }));
    expect(el().querySelector('table.modules-table')).toBeNull();
    expect(el().textContent).toContain('Sin cambios registrados.');
  });

  it('blocks enabling Costeo without valuation and names the missing capability (AC-02, AC-06)', () => {
    const valuation = { key: 'inventory.valuation', label: 'Valoración de Inventario', available: false };
    setup([mod('costing', { capabilities: [valuation], missingCapabilities: ['Valoración de Inventario'] })]);
    expect(button('costing')?.disabled).toBeTrue();
    expect(el().textContent).toContain('Falta la capacidad: Valoración de Inventario');
    expect(el().textContent).toContain('Valoración de Inventario (capacidad)');
  });

  it('shows the adoption date of an enabled Costeo (AC-05, AC-06)', () => {
    setup([mod('costing', { enabled: true, adoptedAt: '2026-10-30T12:00:00+00:00' })]);
    expect(el().textContent).toContain('Adopción: 30/10/2026');
  });

  it('warns that costs are not shown when the capability is lost (EDGE-04)', () => {
    setup([mod('costing', { enabled: true, missingCapabilities: ['Valoración de Inventario'] })]);
    expect(el().textContent).toContain('no se muestran costos');
  });

  it('blocks disabling with open orders and explains how to resolve (AC-04, AC-06)', () => {
    setup([
      mod('production', {
        enabled: true,
        disableBlockers: [{ code: 'open_orders', message: '3 órdenes abiertas', resolution: 'Ciérralas en Elaboraciones' }],
      }),
    ]);
    expect(button('production')?.disabled).toBeTrue();
    expect(el().textContent).toContain('3 órdenes abiertas. Ciérralas en Elaboraciones');
  });
});
