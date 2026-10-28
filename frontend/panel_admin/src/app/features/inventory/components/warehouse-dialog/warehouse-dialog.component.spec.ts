import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';
import { InventoryApiError } from '../../models/api-error';
import { WarehousesApiService } from '../../services/warehouses-api.service';
import { makeWarehouse } from '../../testing/inventory-fixtures';
import { WarehouseDialogComponent } from './warehouse-dialog.component';

describe('WarehouseDialogComponent', () => {
  let fixture: ComponentFixture<WarehouseDialogComponent>;
  let component: WarehouseDialogComponent;
  let api: jasmine.SpyObj<WarehousesApiService>;
  let activeModal: jasmine.SpyObj<NgbActiveModal>;

  beforeEach(async () => {
    api = jasmine.createSpyObj<WarehousesApiService>('WarehousesApiService', ['create', 'update']);
    activeModal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    await TestBed.configureTestingModule({
      imports: [WarehouseDialogComponent],
      providers: [
        { provide: WarehousesApiService, useValue: api },
        { provide: NgbActiveModal, useValue: activeModal },
        { provide: ToastrService, useValue: jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']) },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(WarehouseDialogComponent);
    component = fixture.componentInstance;
  });

  const text = () => (fixture.nativeElement as HTMLElement).textContent ?? '';

  it('requires a name (AC-08)', () => {
    fixture.detectChanges();
    component.onSubmit();
    fixture.detectChanges();
    expect(api.create).not.toHaveBeenCalled();
    expect(text()).toContain('El nombre es obligatorio.');
  });

  it('creates a warehouse and can mark it as default (AC-08)', () => {
    const saved = makeWarehouse({ id: 'w-2', name: 'Bodega', isDefault: true });
    api.create.and.returnValue(of(saved));
    fixture.detectChanges();
    component.form.setValue({ name: ' Bodega ', description: ' Fondo ', isDefault: true });
    component.onSubmit();
    expect(api.create).toHaveBeenCalledWith({ name: 'Bodega', description: 'Fondo', isDefault: true });
    expect(activeModal.close).toHaveBeenCalledWith(saved);
  });

  it('does not let the default warehouse be unmarked here (INV-06)', () => {
    component.edit(makeWarehouse());
    fixture.detectChanges();
    expect(component.form.controls.isDefault.disabled).toBeTrue();
    expect(text()).toContain('define otro almacén como predeterminado');
  });

  it('shows the duplicate-name error under the field', () => {
    api.create.and.returnValue(
      throwError(() => new InventoryApiError('Revisa los datos ingresados.', 400, { name: ['Ya existe un almacén con ese nombre.'] })),
    );
    fixture.detectChanges();
    component.form.patchValue({ name: 'Central' });
    component.onSubmit();
    fixture.detectChanges();
    expect(text()).toContain('Ya existe un almacén con ese nombre.');
    expect(activeModal.close).not.toHaveBeenCalled();
  });
});
