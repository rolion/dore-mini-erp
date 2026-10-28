import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { InventoryApiError } from '../../models/api-error';
import { AdjustmentsApiService } from '../../services/adjustments-api.service';
import { makeAdjustmentDetail } from '../../testing/adjustment-fixtures';
import { AdjustmentDetailComponent } from './adjustment-detail.component';

describe('AdjustmentDetailComponent', () => {
  let fixture: ComponentFixture<AdjustmentDetailComponent>;
  let api: jasmine.SpyObj<AdjustmentsApiService>;

  async function setup(result: ReturnType<AdjustmentsApiService['get']>): Promise<void> {
    api = jasmine.createSpyObj<AdjustmentsApiService>('AdjustmentsApiService', ['get']);
    api.get.and.returnValue(result);
    await TestBed.configureTestingModule({
      imports: [AdjustmentDetailComponent],
      providers: [
        provideRouter([]),
        { provide: AdjustmentsApiService, useValue: api },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: 'a-1' }) } } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(AdjustmentDetailComponent);
    fixture.detectChanges();
  }

  const text = (testId: string): string =>
    (fixture.nativeElement as HTMLElement).querySelector(`[data-testid="${testId}"]`)?.textContent?.replace(/\s+/g, ' ').trim() ?? '';

  it('shows the confirmed adjustment read-only, with the movement link and no actions (AC-06)', async () => {
    await setup(of(makeAdjustmentDetail()));
    expect(api.get).toHaveBeenCalledWith('a-1');
    expect(text('reference')).toBe('AJ-1A2B3C4D');
    expect(text('status')).toBe('Confirmado');
    expect(text('system')).toBe('10 kg');
    expect(text('counted')).toBe('7 kg');
    expect(text('difference')).toBe('-3 kg · Salida de ajuste');
    expect(text('reason')).toBe('Conteo físico');
    const root = fixture.nativeElement as HTMLElement;
    expect(root.querySelector('[data-testid="movement-link"]')?.getAttribute('href')).toBe('/pocketbiz/inventory/movements/m-9');
    const labels = Array.from(root.querySelectorAll('a.btn, button')).map((node) => node.textContent?.trim());
    expect(labels).toEqual(['Volver']);
  });

  it('shows a reversed adjustment as «Revertido» and an entry with a plus sign', async () => {
    await setup(of(makeAdjustmentDetail({ status: 'reversed', kind: 'in', difference: '2.5000' })));
    expect(text('status')).toBe('Revertido');
    expect(text('difference')).toBe('+2.5 kg · Entrada de ajuste');
  });

  it('shows «Ajuste no encontrado.» on a 404', async () => {
    await setup(throwError(() => new InventoryApiError('x', 404)));
    expect(text('error')).toBe('Ajuste no encontrado.');
  });
});
