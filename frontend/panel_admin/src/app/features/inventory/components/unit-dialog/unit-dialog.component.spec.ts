import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';
import { InventoryApiError } from '../../models/api-error';
import { UnitsApiService } from '../../services/units-api.service';
import { makeUnit } from '../../testing/inventory-fixtures';
import { UnitDialogComponent } from './unit-dialog.component';

describe('UnitDialogComponent', () => {
  let fixture: ComponentFixture<UnitDialogComponent>;
  let component: UnitDialogComponent;
  let api: jasmine.SpyObj<UnitsApiService>;
  let activeModal: jasmine.SpyObj<NgbActiveModal>;
  let toastr: jasmine.SpyObj<ToastrService>;

  beforeEach(async () => {
    api = jasmine.createSpyObj<UnitsApiService>('UnitsApiService', ['create', 'update']);
    activeModal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    await TestBed.configureTestingModule({
      imports: [UnitDialogComponent],
      providers: [
        { provide: UnitsApiService, useValue: api },
        { provide: NgbActiveModal, useValue: activeModal },
        { provide: ToastrService, useValue: toastr },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(UnitDialogComponent);
    component = fixture.componentInstance;
  });

  const text = () => (fixture.nativeElement as HTMLElement).textContent ?? '';

  it('requires name and abbreviation (AC-07)', () => {
    fixture.detectChanges();
    expect(text()).toContain('Nueva unidad');
    component.onSubmit();
    fixture.detectChanges();
    expect(api.create).not.toHaveBeenCalled();
    expect(text()).toContain('El nombre es obligatorio.');
    expect(text()).toContain('La abreviatura es obligatoria.');
  });

  it('creates a unit with trimmed values and closes with it (AC-07)', () => {
    const saved = makeUnit();
    api.create.and.returnValue(of(saved));
    fixture.detectChanges();
    component.form.setValue({ name: ' Kilogramo ', abbreviation: ' kg ', allowsFractions: true });
    component.onSubmit();
    expect(api.create).toHaveBeenCalledWith({ name: 'Kilogramo', abbreviation: 'kg', allowsFractions: true });
    expect(activeModal.close).toHaveBeenCalledWith(saved);
  });

  it('shows server field errors and keeps the dialog open (EDGE-02)', () => {
    api.create.and.returnValue(
      throwError(() => new InventoryApiError('Revisa los datos ingresados.', 400, { abbreviation: ['Ya existe una unidad con esa abreviatura.'] })),
    );
    fixture.detectChanges();
    component.form.setValue({ name: 'Kilo', abbreviation: 'kg', allowsFractions: false });
    component.onSubmit();
    fixture.detectChanges();
    expect(activeModal.close).not.toHaveBeenCalled();
    expect(text()).toContain('Ya existe una unidad con esa abreviatura.');
  });

  it('edits an unused unit from its current values (AC-07)', () => {
    api.update.and.returnValue(of(makeUnit({ name: 'Kilos' })));
    component.edit(makeUnit());
    fixture.detectChanges();
    expect(text()).toContain('Editar unidad');
    component.form.controls.name.setValue('Kilos');
    component.onSubmit();
    expect(api.update).toHaveBeenCalledWith('u-1', { name: 'Kilos', abbreviation: 'kg', allowsFractions: true });
  });

  it('locks a unit already assigned to products and explains why (INV-04)', () => {
    component.edit(makeUnit({ inUse: true }));
    fixture.detectChanges();
    expect(component.form.disabled).toBeTrue();
    expect(text()).toContain('solo se puede activar o desactivar');
    expect((fixture.nativeElement as HTMLElement).querySelector('button[type="submit"]')).toBeNull();
    component.onSubmit();
    expect(api.update).not.toHaveBeenCalled();
  });
});
