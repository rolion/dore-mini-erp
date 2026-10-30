import { NgbModal, NgbModalRef } from '@ng-bootstrap/ng-bootstrap';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { AuthService } from '../../../../core/service/auth.service';
import { InventoryApiError } from '../../models/api-error';
import { StockMovementDetail } from '../../models/movement';
import { MovementsApiService } from '../../services/movements-api.service';
import { makeMovementDetail } from '../../testing/inventory-fixtures';
import { MovementDetailComponent } from './movement-detail.component';

describe('MovementDetailComponent', () => {
  let fixture: ComponentFixture<MovementDetailComponent>;
  let api: jasmine.SpyObj<MovementsApiService>;

  async function setup(result: StockMovementDetail | InventoryApiError): Promise<HTMLElement> {
    api = jasmine.createSpyObj<MovementsApiService>('MovementsApiService', ['get']);
    api.get.and.returnValue(result instanceof InventoryApiError ? throwError(() => result) : of(result));
    await TestBed.configureTestingModule({
      imports: [MovementDetailComponent],
      providers: [
        provideRouter([]),
        { provide: MovementsApiService, useValue: api },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: new Map([['id', 'm-1']]) } } },
        { provide: AuthService, useValue: { currentUserValue: { company: { id: 'c', name: 'Empresa Demo' } } } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(MovementDetailComponent);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  it('shows the data needed to reconstruct the operation (AC-06)', async () => {
    const el = await setup(makeMovementDetail());
    const text = el.textContent ?? '';
    const expected = ['m-1', 'Confirmado', 'Empresa Demo', 'Arroz', 'Almacén principal', 'Salida por venta', '2.5000 kg', 'ana', 'PV-1', 'Venta', 'Pedido de venta · 42'];
    for (const value of expected) {
      expect(text).withContext(value).toContain(value);
    }
    expect(api.get).toHaveBeenCalledWith('m-1');
  });

  it('links to the source document when available and has no edit or delete actions (AC-07, AC-08)', async () => {
    const el = await setup(makeMovementDetail());
    expect(el.querySelector('[data-testid="source-link"]')).not.toBeNull();
    expect(el.textContent).not.toContain('Editar');
    expect(el.textContent).not.toContain('Eliminar');
  });

  it('shows the source as plain text when its module is unavailable (AC-07)', async () => {
    const base = makeMovementDetail();
    const el = await setup({ ...base, source: { ...base.source!, available: false } });
    expect(el.querySelector('[data-testid="source-link"]')).toBeNull();
    expect(el.querySelector('[data-testid="source"]')?.textContent).toContain('Pedido de venta');
  });

  it('links counter-movements (AC-06)', async () => {
    const el = await setup(makeMovementDetail({ status: 'reversed', reversedById: 'm-9' }));
    expect(el.querySelector('[data-testid="status"]')?.textContent).toContain('Revertido');
    expect(el.querySelector('[data-testid="counter"] a')?.getAttribute('href')).toContain('m-9');
  });

  it('shows no source and no counter-movements when there are none', async () => {
    const el = await setup(makeMovementDetail({ source: null }));
    expect(el.querySelector('[data-testid="source"]')?.textContent).toContain('Sin documento de origen');
    expect(el.querySelector('[data-testid="counter"]')?.textContent).toContain('Ninguno');
  });

  it('shows not found for a 404', async () => {
    const el = await setup(new InventoryApiError('x', 404));
    expect(el.querySelector('[data-testid="error"]')?.textContent).toContain('Movimiento no encontrado.');
  });

  it('offers «Revertir» only when the server allows it and the movement is confirmed (AC-12, AC-15)', async () => {
    const el = await setup(makeMovementDetail({ source: null, reversal: { allowed: true, code: null, message: null } }));
    expect(el.querySelector('[data-testid="reverse"]')).not.toBeNull();
    expect(el.querySelector('[data-testid="reverse-blocked"]')).toBeNull();
  });

  it('explains why a sale movement cannot be reversed here (AC-04, AC-15)', async () => {
    const message = 'Las salidas por venta requieren una devolución, que aún no está disponible.';
    const el = await setup(makeMovementDetail({ reversal: { allowed: false, code: 'requires_return', message } }));
    expect(el.querySelector('[data-testid="reverse"]')).toBeNull();
    expect(el.querySelector('[data-testid="reverse-blocked"]')?.textContent).toContain('devolución');
  });

  it('offers no second reversal for a reversed movement nor for a counter-movement (AC-03, AC-15)', async () => {
    const blocked = { allowed: false, code: 'already_reversed', message: 'El movimiento ya fue revertido.' };
    const el = await setup(makeMovementDetail({ status: 'reversed', reversal: blocked, reversedById: 'm-9' }));
    expect(el.querySelector('[data-testid="reverse"]')).toBeNull();
    expect(el.querySelector('[data-testid="reverse-blocked"]')).toBeNull();
  });

  it('shows the reversal block with counter-movement, user, date and reason (AC-11, AC-15)', async () => {
    const reversedBy = { id: 'm-9', reference: 'AJ-9', occurredAt: '2026-10-21T10:00:00Z', reason: 'Error de carga', userName: 'bea' };
    const el = await setup(makeMovementDetail({ status: 'reversed', reversedBy, reversedById: 'm-9', reversal: { allowed: false, code: 'already_reversed', message: 'x' } }));
    expect(el.querySelector('[data-testid="reversal-link"]')?.getAttribute('href')).toContain('m-9');
    expect(el.querySelector('[data-testid="reversal-user"]')?.textContent).toContain('bea');
    expect(el.querySelector('[data-testid="reversal-date"]')?.textContent).toMatch(/21\/10\/2026/);
    expect(el.querySelector('[data-testid="reversal-reason"]')?.textContent).toContain('Error de carga');
  });

  it('opens the dialog, reloads and confirms after reversing (AC-15)', async () => {
    const el = await setup(makeMovementDetail({ source: null }));
    const modal = TestBed.inject(NgbModal);
    const dialog = { init: jasmine.createSpy('init') };
    spyOn(modal, 'open').and.returnValue({ componentInstance: dialog, result: Promise.resolve(makeMovementDetail()) } as unknown as NgbModalRef);
    (el.querySelector('[data-testid="reverse"]') as HTMLButtonElement).click();
    await fixture.whenStable();
    fixture.detectChanges();
    expect(dialog.init).toHaveBeenCalledWith(jasmine.objectContaining({ id: 'm-1', kind: 'out', productName: 'Arroz' }));
    expect(api.get).toHaveBeenCalledTimes(2);
    expect(el.querySelector('[data-testid="success"]')?.textContent).toContain('Movimiento revertido');
  });

  it('does not reload when the dialog is dismissed', async () => {
    const el = await setup(makeMovementDetail({ source: null }));
    spyOn(TestBed.inject(NgbModal), 'open').and.returnValue({ componentInstance: { init: () => undefined }, result: Promise.reject(undefined) } as unknown as NgbModalRef);
    (el.querySelector('[data-testid="reverse"]') as HTMLButtonElement).click();
    await fixture.whenStable();
    expect(api.get).toHaveBeenCalledTimes(1);
  });
});
