import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';
import { ModuleSettings, Setting, SettingHistoryPage, SettingsApiError } from '../../models/setting';
import { SettingsApiService } from '../../services/settings-api.service';
import { ModuleSettingsComponent, SAVED_MESSAGE } from './module-settings.component';

const PERCENT = 'sales.max_discount_percent';
const CHANNEL = 'sales.default_sales_channel';

function setting(extra: Partial<Setting>): Setting {
  return {
    key: PERCENT,
    label: 'Descuento máximo (% del subtotal)',
    description: 'Aplica a los descuentos que se registren desde ahora.',
    kind: 'percent',
    value: '100.00',
    default: '100.00',
    choices: [],
    minimum: '0',
    maximum: '100',
    ...extra,
  };
}

const SALES: ModuleSettings = {
  module: 'sales',
  settings: [
    setting({ key: CHANNEL, label: 'Canal de venta predeterminado', kind: 'choice', value: '', default: '', choices: [{ value: 'FAIR', label: 'Feria' }] }),
    setting({}),
  ],
};
const NEGATIVE = 'inventory.allow_negative_stock';
const INVENTORY: ModuleSettings = {
  module: 'inventory',
  settings: [
    setting({
      key: NEGATIVE,
      label: 'Permitir stock negativo',
      description: 'Afecta entregas, ajustes y reversión de recepciones.',
      kind: 'boolean',
      value: 'false',
      default: 'false',
      minimum: null,
      maximum: null,
    }),
  ],
};
const EMPTY_HISTORY: SettingHistoryPage = { count: 0, results: [], settings: [] };

describe('ModuleSettingsComponent', () => {
  let fixture: ComponentFixture<ModuleSettingsComponent>;
  let component: ModuleSettingsComponent;
  let api: jasmine.SpyObj<SettingsApiService>;
  let toastr: jasmine.SpyObj<ToastrService>;

  const el = () => fixture.nativeElement as HTMLElement;
  const button = (text: string) =>
    Array.from(el().querySelectorAll<HTMLButtonElement>('button')).find((b) => b.textContent?.trim() === text) ?? null;

  const setup = (module = 'sales', result: ModuleSettings = SALES) => {
    api.get.and.returnValue(of(result));
    TestBed.overrideProvider(ActivatedRoute, { useValue: { snapshot: { data: { settingsModule: module } } } });
    fixture = TestBed.createComponent(ModuleSettingsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  };

  beforeEach(() => {
    api = jasmine.createSpyObj<SettingsApiService>('SettingsApiService', ['get', 'save', 'history']);
    api.history.and.returnValue(of(EMPTY_HISTORY));
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    TestBed.configureTestingModule({
      imports: [ModuleSettingsComponent],
      providers: [
        provideRouter([]),
        { provide: SettingsApiService, useValue: api },
        { provide: ToastrService, useValue: toastr },
        { provide: ActivatedRoute, useValue: { snapshot: { data: {} } } },
      ],
    });
  });

  it('shows label, description, current and default value of each setting (AC-02, UI-02)', () => {
    setup();
    expect(el().textContent).toContain('Configuración de Ventas');
    expect(el().textContent).toContain('Canal de venta predeterminado');
    expect(el().textContent).toContain('Aplica a los descuentos que se registren desde ahora.');
    expect(el().textContent).toContain('Valor predeterminado: 100.00 %');
    expect((el().querySelector(`#setting-${PERCENT.replace(/\./g, '\\.')}`) as HTMLInputElement).value).toBe('100.00');
  });

  it('offers General and Historial de cambios tabs (AC-09)', () => {
    setup();
    expect(button('General')).not.toBeNull();
    button('Historial de cambios')?.click();
    fixture.detectChanges();
    expect(api.history).toHaveBeenCalledWith('sales', jasmine.objectContaining({ page: 1 }));
    expect(el().textContent).toContain('Sin cambios registrados.');
  });

  it('shows the no-settings notice for modules without settings and no save buttons (AC-09)', () => {
    setup('purchases', { module: 'purchases', settings: [] });
    expect(el().textContent).toContain('aún no tiene ajustes configurables');
    expect(button('Guardar cambios')).toBeNull();
    button('Historial de cambios')?.click();
    fixture.detectChanges();
    expect(api.history).toHaveBeenCalledWith('purchases', jasmine.anything());
  });

  it('keeps save and cancel disabled until something changes (AC-10)', () => {
    setup();
    expect(button('Guardar cambios')?.disabled).toBeTrue();
    expect(button('Cancelar cambios')?.disabled).toBeTrue();
    component.form.controls[PERCENT].setValue('50');
    fixture.detectChanges();
    expect(button('Guardar cambios')?.disabled).toBeFalse();
    expect(component.hasUnsavedChanges()).toBeTrue();
  });

  it('treats 100 and 100.00 as the same value', () => {
    setup();
    component.form.controls[PERCENT].setValue('100');
    expect(component.dirty).toBeFalse();
  });

  it('saves only the changed settings and shows success (AC-10)', () => {
    setup();
    api.save.and.returnValue(of({ module: 'sales', settings: [setting({ value: '50.00' }), SALES.settings[0]] }));
    component.form.controls[PERCENT].setValue('50');
    component.save();
    expect(api.save).toHaveBeenCalledOnceWith('sales', { [PERCENT]: '50' });
    expect(toastr.success).toHaveBeenCalledWith(SAVED_MESSAGE);
    expect(component.hasUnsavedChanges()).toBeFalse();
  });

  it('shows the server error next to the field and keeps what was typed (AC-10, EDGE-07)', () => {
    setup();
    api.save.and.returnValue(throwError(() => new SettingsApiError('x', 400, { [PERCENT]: 'Debe estar entre 0 y 100.' })));
    component.form.controls[PERCENT].setValue('500');
    component.save();
    fixture.detectChanges();
    expect(el().textContent).toContain('Debe estar entre 0 y 100.');
    expect(component.form.controls[PERCENT].value).toBe('500');
    expect(button('Guardar cambios')?.disabled).toBeFalse();
    expect(toastr.success).not.toHaveBeenCalled();
  });

  it('shows a general error for network failures and keeps the data (EDGE-07)', () => {
    setup();
    api.save.and.returnValue(throwError(() => new SettingsApiError('Sin conexión.', 0)));
    component.form.controls[PERCENT].setValue('20');
    component.save();
    fixture.detectChanges();
    expect(el().querySelector('.alert-danger')?.textContent).toContain('Sin conexión.');
    expect(component.form.controls[PERCENT].value).toBe('20');
  });

  it('cancel restores the last saved values (AC-10)', () => {
    setup();
    component.form.controls[PERCENT].setValue('20');
    component.cancel();
    expect(component.form.controls[PERCENT].value).toBe('100.00');
    expect(component.hasUnsavedChanges()).toBeFalse();
  });

  it('restore default only fills the control without saving (UI-02)', () => {
    setup('sales', { module: 'sales', settings: [setting({ value: '30.00' })] });
    component.restoreDefault(component.settings[0]);
    expect(component.form.controls[PERCENT].value).toBe('100.00');
    expect(api.save).not.toHaveBeenCalled();
  });

  it('warns before the tab is closed only with unsaved changes (UI-05)', () => {
    setup();
    const clean = new Event('beforeunload', { cancelable: true }) as BeforeUnloadEvent;
    component.warnBeforeUnload(clean);
    expect(clean.defaultPrevented).toBeFalse();
    component.form.controls[PERCENT].setValue('1');
    const dirty = new Event('beforeunload', { cancelable: true }) as BeforeUnloadEvent;
    component.warnBeforeUnload(dirty);
    expect(dirty.defaultPrevented).toBeTrue();
  });

  it('shows a load error with retry', () => {
    api.get.and.returnValue(throwError(() => new SettingsApiError('Falló.', 500)));
    TestBed.overrideProvider(ActivatedRoute, { useValue: { snapshot: { data: { settingsModule: 'sales' } } } });
    fixture = TestBed.createComponent(ModuleSettingsComponent);
    fixture.detectChanges();
    expect(el().textContent).toContain('Falló.');
    expect(button('Reintentar')).not.toBeNull();
  });

  describe('boolean setting «Permitir stock negativo» (AC-05)', () => {
    let modal: jasmine.SpyObj<NgbModal>;
    const toggle = () => el().querySelector('input[type="checkbox"]') as HTMLInputElement;
    const flipOn = () => {
      toggle().checked = true;
      toggle().dispatchEvent(new Event('change'));
      fixture.detectChanges();
    };
    const dialog = (result: Promise<unknown>) => {
      modal.open.and.returnValue({ componentInstance: {}, result } as never);
    };

    beforeEach(() => {
      modal = jasmine.createSpyObj<NgbModal>('NgbModal', ['open']);
      TestBed.overrideProvider(NgbModal, { useValue: modal });
    });

    it('renders a switch off by default with description and default value', () => {
      setup('inventory', INVENTORY);
      expect(toggle().checked).toBeFalse();
      expect(toggle().getAttribute('role')).toBe('switch');
      expect(el().textContent).toContain('Permitir stock negativo');
      expect(el().textContent).toContain('Afecta entregas, ajustes y reversión de recepciones.');
      expect(el().textContent).toContain('Valor predeterminado: Desactivado');
    });

    it('asks for confirmation before saving it enabled and saves on accept', async () => {
      setup('inventory', INVENTORY);
      dialog(Promise.resolve(true));
      api.save.and.returnValue(of({ module: 'inventory', settings: [{ ...INVENTORY.settings[0], value: 'true' }] }));
      flipOn();
      component.save();
      await fixture.whenStable();
      expect(modal.open).toHaveBeenCalledTimes(1);
      expect(api.save).toHaveBeenCalledOnceWith('inventory', { [NEGATIVE]: 'true' });
      expect(toastr.success).toHaveBeenCalledWith(SAVED_MESSAGE);
    });

    it('does not save and keeps the switch when the confirmation is cancelled', async () => {
      setup('inventory', INVENTORY);
      dialog(Promise.reject(new Error('dismissed')));
      flipOn();
      component.save();
      await fixture.whenStable();
      expect(api.save).not.toHaveBeenCalled();
      expect(component.control(INVENTORY.settings[0]).value).toBe('true');
      expect(component.hasUnsavedChanges()).toBeTrue();
    });

    it('saves it disabled without asking', () => {
      setup('inventory', { module: 'inventory', settings: [{ ...INVENTORY.settings[0], value: 'true' }] });
      api.save.and.returnValue(of(INVENTORY));
      toggle().checked = false;
      toggle().dispatchEvent(new Event('change'));
      component.save();
      expect(modal.open).not.toHaveBeenCalled();
      expect(api.save).toHaveBeenCalledOnceWith('inventory', { [NEGATIVE]: 'false' });
    });
  });
});
