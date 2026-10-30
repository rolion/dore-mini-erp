import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';
import { AppModule, ModulesApiError } from '../../../../core/models/module';
import { AuthService } from '../../../../core/service/auth.service';
import { ModulesService } from '../../../../core/service/modules.service';
import { ModuleConfirmDialogComponent } from './module-confirm-dialog.component';

const MODULE: AppModule = {
  key: 'sales',
  name: 'Ventas',
  description: '',
  isBase: false,
  enabled: true,
  requires: [{ key: 'catalog', name: 'Catálogo', enabled: true }],
  optional: [],
  missingRequires: [],
  capabilities: [],
  missingCapabilities: [],
  adoptedAt: null,
  disableBlockers: [],
};

describe('ModuleConfirmDialogComponent', () => {
  let fixture: ComponentFixture<ModuleConfirmDialogComponent>;
  let component: ModuleConfirmDialogComponent;
  let service: jasmine.SpyObj<ModulesService>;
  let activeModal: jasmine.SpyObj<NgbActiveModal>;
  let toastr: jasmine.SpyObj<ToastrService>;

  beforeEach(async () => {
    service = jasmine.createSpyObj<ModulesService>('ModulesService', ['enable', 'disable']);
    activeModal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    await TestBed.configureTestingModule({
      imports: [ModuleConfirmDialogComponent],
      providers: [
        { provide: ModulesService, useValue: service },
        { provide: NgbActiveModal, useValue: activeModal },
        { provide: ToastrService, useValue: toastr },
        { provide: AuthService, useValue: { currentUserValue: { company: { id: 'c', name: 'Cuñapés SRL' } } } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(ModuleConfirmDialogComponent);
    component = fixture.componentInstance;
    component.module = MODULE;
  });

  const text = () => (fixture.nativeElement as HTMLElement).textContent ?? '';

  it('summarises module, company and affected modules before confirming (AC-07)', () => {
    component.action = 'disable';
    component.affected = ['Reportes'];
    fixture.detectChanges();
    expect(text()).toContain('Deshabilitar módulo');
    expect(text()).toContain('Ventas');
    expect(text()).toContain('Cuñapés SRL');
    expect(text()).toContain('Catálogo');
    expect(text()).toContain('Reportes');
  });

  it('enables and closes the dialog on confirm', () => {
    service.enable.and.returnValue(of(MODULE));
    fixture.detectChanges();
    component.confirm();
    expect(service.enable).toHaveBeenCalledWith('sales');
    expect(toastr.success).toHaveBeenCalledWith('Módulo habilitado');
    expect(activeModal.close).toHaveBeenCalledWith(MODULE);
  });

  it('shows the server error and keeps the dialog open (AC-03)', () => {
    service.enable.and.returnValue(
      throwError(() => new ModulesApiError('Faltan módulos por habilitar: Gastos.', 409, ['Gastos'])),
    );
    fixture.detectChanges();
    component.confirm();
    fixture.detectChanges();
    expect(text()).toContain('Faltan módulos por habilitar: Gastos.');
    expect(activeModal.close).not.toHaveBeenCalled();
    expect(component.saving).toBeFalse();
  });

  it('announces the adoption date and no retroactive costing when enabling Costeo (AC-05)', () => {
    component.module = {
      ...MODULE,
      key: 'costing',
      name: 'Costeo',
      enabled: false,
      capabilities: [{ key: 'inventory.valuation', label: 'Valoración de Inventario', available: true }],
    };
    component.action = 'enable';
    fixture.detectChanges();
    expect(text()).toContain('Fecha de adopción');
    expect(text()).toContain('No se recalculan lotes anteriores; se valoran las existencias actuales.');
    expect(text()).toContain('Valoración de Inventario');
  });

  it('lists the blockers instead of the reassurance when disabling with open data (AC-04)', () => {
    component.module = {
      ...MODULE,
      disableBlockers: [{ code: 'open_orders', message: '3 órdenes abiertas', resolution: 'Ciérralas' }],
    };
    component.action = 'disable';
    fixture.detectChanges();
    expect(text()).toContain('3 órdenes abiertas. Ciérralas');
    expect(text()).not.toContain('Tus datos e historial se conservan');
  });
});
