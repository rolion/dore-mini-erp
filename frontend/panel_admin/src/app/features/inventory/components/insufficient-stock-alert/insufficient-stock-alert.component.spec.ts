import { ComponentFixture, TestBed } from '@angular/core/testing';
import { InsufficientStockAlertComponent } from './insufficient-stock-alert.component';

describe('InsufficientStockAlertComponent', () => {
  let fixture: ComponentFixture<InsufficientStockAlertComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [InsufficientStockAlertComponent] });
    fixture = TestBed.createComponent(InsufficientStockAlertComponent);
    fixture.componentRef.setInput('info', {
      productName: 'Harina',
      warehouseName: 'Central',
      requested: '5.000',
      available: '2.000',
      unit: 'kg',
    });
    fixture.detectChanges();
  });

  it('shows product, warehouse, requested quantity and current stock (AC-06)', () => {
    const text = (fixture.nativeElement as HTMLElement).textContent?.replace(/\s+/g, ' ') ?? '';
    expect(text).toContain('No hay existencia suficiente.');
    expect(text).toContain('Harina');
    expect(text).toContain('Central');
    expect(text).toContain('Cantidad solicitada5.000 kg');
    expect(text).toContain('Existencia actual2.000 kg');
    expect((fixture.nativeElement as HTMLElement).querySelector('[role="alert"]')).not.toBeNull();
  });
});
