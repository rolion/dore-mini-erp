import { provideTestTranslations } from '../../../core/i18n/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Dentition, Finding } from '../models/odontogram';
import { makeCatalog } from '../testing/odontogram-fixtures';
import { OdontogramChartComponent } from './odontogram-chart.component';

describe('OdontogramChartComponent (AC-11, AC-12)', () => {
  let fixture: ComponentFixture<OdontogramChartComponent>;
  const root = () => fixture.nativeElement as HTMLElement;
  const tooth = (piece: number) => root().querySelector<HTMLButtonElement>(`[data-piece="${piece}"]`) as HTMLButtonElement;
  async function setup(dentition: Dentition, findings: Finding[] = [], selected: number | null = null) {
    await TestBed.configureTestingModule({ imports: [OdontogramChartComponent], providers: provideTestTranslations() }).compileComponents();
    fixture = TestBed.createComponent(OdontogramChartComponent);
    fixture.componentRef.setInput('dentition', dentition);
    fixture.componentRef.setInput('catalog', makeCatalog());
    fixture.componentRef.setInput('findings', findings);
    fixture.componentRef.setInput('selected', selected);
    fixture.detectChanges();
  }
  const caries: Finding = { piece: 16, surfaces: ['O'], condition: 'caries', diagnosis: '', notes: '' };

  it('draws 32 permanent pieces, 20 temporary pieces and both sets in mixed dentition', async () => {
    await setup('permanent');
    expect(root().querySelectorAll('.odo-tooth').length).toBe(32);
    fixture.componentRef.setInput('dentition', 'temporary'); fixture.detectChanges();
    expect(root().querySelectorAll('.odo-tooth').length).toBe(20);
    fixture.componentRef.setInput('dentition', 'mixed'); fixture.detectChanges();
    expect(root().querySelectorAll('.odo-tooth').length).toBe(52);
    expect(root().querySelector('[data-piece="54"]')?.classList).toContain('temporary');
    expect(root().querySelector('[data-piece="16"]')?.classList).not.toContain('temporary');
    expect(tooth(54).textContent).toContain('T');
    expect(tooth(16).textContent).toContain('P');
  });

  it('shows "Sin evaluar" for pieces without findings and abbreviation text for evaluated pieces', async () => {
    await setup('mixed', [caries, { piece: 54, surfaces: [], condition: 'healthy', diagnosis: '', notes: '' }]);
    expect(tooth(11).getAttribute('aria-label')).toContain('Sin evaluar');
    expect(tooth(11).textContent).toContain('S/E');
    expect(tooth(16).textContent).toContain('CAR');
    expect(tooth(16).getAttribute('aria-label')).toContain('Caries (O)');
    expect(tooth(54).textContent).toContain('SAN');
    expect(tooth(16).querySelector('polygon[data-surface="O"]')?.getAttribute('class')).toContain('fill-danger');
  });

  it('has a textual legend with abbreviation and name', async () => {
    await setup('permanent');
    const legend = root().querySelector('.odo-legend')?.textContent ?? '';
    expect(legend).toContain('CAR'); expect(legend).toContain('Caries'); expect(legend).toContain('Sin evaluar');
  });

  it('emits the selected piece and marks it as pressed', async () => {
    await setup('permanent', [], 16);
    const emitted: number[] = [];
    fixture.componentInstance.pieceSelected.subscribe(piece => emitted.push(piece));
    tooth(26).click();
    expect(emitted).toEqual([26]);
    expect(tooth(16).getAttribute('aria-pressed')).toBe('true');
    expect(tooth(16).getAttribute('tabindex')).toBe('0');
    expect(tooth(26).getAttribute('tabindex')).toBe('-1');
  });

  it('moves focus with the arrow keys inside and between arches', async () => {
    await setup('permanent');
    document.body.appendChild(root());
    tooth(18).dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
    expect(document.activeElement).toBe(tooth(17));
    tooth(17).dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }));
    expect(document.activeElement).toBe(tooth(47));
    tooth(47).dispatchEvent(new KeyboardEvent('keydown', { key: 'End', bubbles: true }));
    expect(document.activeElement).toBe(tooth(38));
    root().remove();
  });
});
