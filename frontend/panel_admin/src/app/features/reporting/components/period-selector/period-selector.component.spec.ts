import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { PeriodSelection } from '../../models/report';
import { MONTH } from '../../testing/report-fixtures';
import { INVALID_RANGE_MESSAGE, PeriodSelectorComponent } from './period-selector.component';

describe('PeriodSelectorComponent', () => {
  let fixture: ComponentFixture<PeriodSelectorComponent>;
  let component: PeriodSelectorComponent;
  let emitted: PeriodSelection[];

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [PeriodSelectorComponent] }).compileComponents();
    fixture = TestBed.createComponent(PeriodSelectorComponent);
    component = fixture.componentInstance;
    emitted = [];
    component.selectionChange.subscribe((s) => emitted.push(s));
    fixture.detectChanges();
  });

  const text = () => (fixture.nativeElement as HTMLElement).textContent ?? '';
  const click = (kind: string) => {
    (fixture.debugElement.query(By.css(`[data-kind="${kind}"]`)).nativeElement as HTMLElement).click();
    fixture.detectChanges();
  };

  it('offers day, week, month and range, with month selected (AC-25)', () => {
    const labels = fixture.debugElement.queryAll(By.css('[data-kind]')).map((b) => (b.nativeElement as HTMLElement).textContent?.trim());
    expect(labels).toEqual(['Hoy', 'Esta semana', 'Este mes', 'Rango']);
    expect(component.kind).toBe('month');
  });

  it('emits the named period when clicked, without computing dates (AC-25)', () => {
    click('day');
    click('week');
    click('month');
    expect(emitted).toEqual([{ kind: 'day' }, { kind: 'week' }, { kind: 'month' }]);
  });

  it('shows the range form and emits only a valid range (AC-25)', () => {
    click('range');
    expect(emitted).toEqual([]);
    expect(fixture.debugElement.query(By.css('[data-testid="range-form"]'))).not.toBeNull();

    component.applyRange();
    fixture.detectChanges();
    expect(emitted).toEqual([]);
    expect(text()).toContain(INVALID_RANGE_MESSAGE);

    component.rangeForm.setValue({ dateFrom: '2026-10-20', dateTo: '2026-10-10' });
    component.applyRange();
    expect(emitted).toEqual([]);

    component.rangeForm.setValue({ dateFrom: '2026-10-01', dateTo: '2026-10-20' });
    component.applyRange();
    fixture.detectChanges();
    expect(emitted).toEqual([{ kind: 'range', dateFrom: '2026-10-01', dateTo: '2026-10-20' }]);
    expect(text()).not.toContain(INVALID_RANGE_MESSAGE);
  });

  it('accepts a single-day range', () => {
    click('range');
    component.rangeForm.setValue({ dateFrom: '2026-10-05', dateTo: '2026-10-05' });
    component.applyRange();
    expect(emitted).toEqual([{ kind: 'range', dateFrom: '2026-10-05', dateTo: '2026-10-05' }]);
  });

  it('shows the effective dates from the server (AC-25)', () => {
    fixture.componentRef.setInput('effective', MONTH);
    fixture.detectChanges();
    expect(text()).toContain('Del 01/10/2026 al 31/10/2026');
    fixture.componentRef.setInput('effective', { kind: 'day', dateFrom: '2026-10-14', dateTo: '2026-10-14' });
    fixture.detectChanges();
    expect(text()).toContain('Día 14/10/2026');
  });
});
