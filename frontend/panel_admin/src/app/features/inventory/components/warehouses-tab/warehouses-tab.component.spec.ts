import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';
import { InventoryApiError } from '../../models/api-error';
import { WarehousesApiService } from '../../services/warehouses-api.service';
import { makeWarehouse } from '../../testing/inventory-fixtures';
import { WarehousesTabComponent } from './warehouses-tab.component';

describe('WarehousesTabComponent', () => {
  let fixture: ComponentFixture<WarehousesTabComponent>;
  let component: WarehousesTabComponent;
  let api: jasmine.SpyObj<WarehousesApiService>;
  let toastr: jasmine.SpyObj<ToastrService>;

  const main = makeWarehouse();
  const second = makeWarehouse({ id: 'w-2', name: 'Sucursal', isDefault: false });

  beforeEach(async () => {
    api = jasmine.createSpyObj<WarehousesApiService>('WarehousesApiService', ['list', 'activate', 'deactivate', 'makeDefault']);
    api.list.and.returnValue(of({ count: 2, next: null, previous: null, results: [main, second] }));
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    await TestBed.configureTestingModule({
      imports: [WarehousesTabComponent],
      providers: [
        { provide: WarehousesApiService, useValue: api },
        { provide: ToastrService, useValue: toastr },
        { provide: NgbModal, useValue: jasmine.createSpyObj<NgbModal>('NgbModal', ['open']) },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(WarehousesTabComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  const el = () => fixture.nativeElement as HTMLElement;

  it('lists only active warehouses by default and marks the default one (AC-08)', () => {
    expect(api.list.calls.mostRecent().args[0]?.active).toBeTrue();
    const rows = el().querySelectorAll('tbody tr');
    expect(rows.length).toBe(2);
    expect(rows[0].textContent).toContain('Predeterminado');
  });

  it('offers «Definir predeterminado» only on active non-default warehouses (AC-08)', () => {
    const rows = el().querySelectorAll('tbody tr');
    expect(rows[0].querySelector('[aria-label="Definir predeterminado"]')).toBeNull();
    expect(rows[1].querySelector('[aria-label="Definir predeterminado"]')).not.toBeNull();
  });

  it('makes a warehouse the default and reloads (AC-08)', () => {
    api.makeDefault.and.returnValue(of({ ...second, isDefault: true }));
    component.makeDefault(second);
    expect(api.makeDefault).toHaveBeenCalledWith('w-2');
    expect(toastr.success).toHaveBeenCalled();
    expect(api.list).toHaveBeenCalledTimes(2);
  });

  it('shows the reason when deactivation is blocked and does not reload (AC-09)', () => {
    api.deactivate.and.returnValue(
      throwError(() => new InventoryApiError('No se puede desactivar: el almacén tiene saldo distinto de cero.', 409, {}, 'warehouse_has_stock')),
    );
    component.toggleActive(second);
    fixture.detectChanges();
    expect(el().querySelector('.alert-warning')?.textContent).toContain('saldo distinto de cero');
    expect(api.list).toHaveBeenCalledTimes(1);
    expect(toastr.error).not.toHaveBeenCalled();
  });

  it('shows an error with retry when loading fails', () => {
    api.list.and.returnValue(throwError(() => new InventoryApiError('No se pudo conectar con el servidor.', 0)));
    component.reload();
    fixture.detectChanges();
    expect(el().textContent).toContain('No se pudo conectar con el servidor.');
    expect(el().textContent).toContain('Reintentar');
  });
});
