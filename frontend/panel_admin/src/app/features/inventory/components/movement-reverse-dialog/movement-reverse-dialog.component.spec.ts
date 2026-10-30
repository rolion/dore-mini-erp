import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { of, throwError } from 'rxjs';
import { InventoryApiError } from '../../models/api-error';
import { MovementsApiService } from '../../services/movements-api.service';
import { makeMovementDetail } from '../../testing/inventory-fixtures';
import { MovementReverseDialogComponent } from './movement-reverse-dialog.component';

describe('MovementReverseDialogComponent', () => {
  let fixture: ComponentFixture<MovementReverseDialogComponent>;
  let component: MovementReverseDialogComponent;
  let activeModal: jasmine.SpyObj<NgbActiveModal>;
  let api: jasmine.SpyObj<MovementsApiService>;

  beforeEach(async () => {
    activeModal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    api = jasmine.createSpyObj<MovementsApiService>('MovementsApiService', ['reverse']);
    await TestBed.configureTestingModule({
      imports: [MovementReverseDialogComponent],
      providers: [
        { provide: NgbActiveModal, useValue: activeModal },
        { provide: MovementsApiService, useValue: api },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(MovementReverseDialogComponent);
    component = fixture.componentInstance;
    component.init({
      id: 'm-1',
      reference: 'AJ-1',
      typeLabel: 'Entrada de ajuste',
      productName: 'Arroz',
      warehouseName: 'Central',
      quantity: '3.0000',
      unitAbbreviation: 'kg',
      kind: 'in',
    });
    fixture.detectChanges();
  });

  const el = (): HTMLElement => fixture.nativeElement as HTMLElement;
  const byId = (id: string): HTMLElement | null => el().querySelector<HTMLElement>(`[data-testid="${id}"]`);
  const type = (value: string): void => {
    component.form.controls.reason.setValue(value);
    fixture.detectChanges();
  };

  it('shows the original movement and the inverse effect (AC-15)', () => {
    expect(byId('reference')?.textContent).toContain('AJ-1');
    expect(byId('type')?.textContent).toContain('Entrada de ajuste');
    expect(byId('product')?.textContent).toContain('Arroz');
    expect(byId('warehouse')?.textContent).toContain('Central');
    expect(byId('quantity')?.textContent).toContain('3.0000 kg');
    expect(byId('effect')?.textContent).toContain('Se registrará una salida de 3.0000 kg en Central.');
  });

  it('keeps the button disabled until there is a reason and limits it to 200 characters (AC-01)', () => {
    expect((byId('reverse-movement') as HTMLButtonElement).disabled).toBeTrue();
    type('   ');
    expect((byId('reverse-movement') as HTMLButtonElement).disabled).toBeTrue();
    type('Error de carga');
    expect((byId('reverse-movement') as HTMLButtonElement).disabled).toBeFalse();
    expect(el().querySelector('textarea')?.getAttribute('maxlength')).toBe('200');
  });

  it('sends the trimmed reason and closes with the counter-movement (AC-02)', () => {
    const counter = makeMovementDetail({ id: 'm-2' });
    api.reverse.and.returnValue(of(counter));
    type('  Error de carga  ');
    component.submit();
    expect(api.reverse).toHaveBeenCalledWith('m-1', 'Error de carga');
    expect(activeModal.close).toHaveBeenCalledWith(counter);
  });

  it('shows product and balance on insufficient stock without closing (AC-05)', () => {
    api.reverse.and.returnValue(
      throwError(() => new InventoryApiError('x', 409, {}, 'insufficient_stock', [], [], null, { productName: 'Arroz', warehouseName: 'Central', requested: '3.000', available: '1.000', unit: 'kg' })),
    );
    type('Error');
    component.submit();
    fixture.detectChanges();
    expect(activeModal.close).not.toHaveBeenCalled();
    expect(byId('insufficient-stock')?.textContent).toContain('Arroz');
    expect(byId('stock-available')?.textContent).toContain('1.000 kg');
    expect(component.form.controls.reason.value).toBe('Error');
  });

  it('shows other server conflicts and field errors inside the dialog (AC-04)', () => {
    api.reverse.and.returnValue(throwError(() => new InventoryApiError('El movimiento ya fue revertido.', 409, {}, 'already_reversed')));
    type('Error');
    component.submit();
    fixture.detectChanges();
    expect(byId('error')?.textContent).toContain('ya fue revertido');
    api.reverse.and.returnValue(throwError(() => new InventoryApiError('x', 400, { reason: ['El motivo es obligatorio.'] })));
    component.submit();
    fixture.detectChanges();
    expect(byId('reason-error')?.textContent).toContain('obligatorio');
  });

  it('«Volver» dismisses without changes', () => {
    byId('back')?.click();
    expect(activeModal.dismiss).toHaveBeenCalled();
    expect(api.reverse).not.toHaveBeenCalled();
  });
});
