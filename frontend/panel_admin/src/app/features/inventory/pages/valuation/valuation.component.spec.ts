import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { Observable, of, throwError } from 'rxjs';
import { Adoption, Proposal, Valuation } from '../../models/valuation';
import { ValuationApiError, ValuationApiService } from '../../services/valuation-api.service';
import { STOCK_CHANGED_MESSAGE, ValuationComponent } from './valuation.component';

const PROPOSAL: Proposal = {
  lines: [
    {
      productId: 'p-1',
      productName: 'Harina',
      unitAbbreviation: 'kg',
      reconciledQuantity: '3.0000',
      warehouses: [{ warehouseId: 'w-1', warehouseName: 'Central', quantity: '3.0000' }],
    },
  ],
  blockers: [],
};

const ADOPTION: Adoption = {
  id: 'a-1',
  cutoffAt: '2026-10-30T12:00:00Z',
  method: 'weighted_moving_average',
  userName: 'ana',
  lines: [
    {
      productId: 'p-1',
      productName: 'Harina',
      unitAbbreviation: 'kg',
      reconciledQuantity: '3.0000',
      totalValue: '10.00',
      unitCost: '3.333333',
      declaredZero: false,
      source: 'Ingreso manual',
    },
  ],
};

describe('ValuationComponent', () => {
  function create(options: { valuation?: Valuation; proposal?: Proposal; adopt?: Observable<Adoption> } = {}) {
    const api = jasmine.createSpyObj<ValuationApiService>('ValuationApiService', ['get', 'proposal', 'adopt']);
    api.get.and.returnValue(of(options.valuation ?? { status: 'not_adopted', adoption: null }));
    api.proposal.and.returnValue(of(options.proposal ?? PROPOSAL));
    api.adopt.and.returnValue(options.adopt ?? of(ADOPTION));
    const toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    TestBed.configureTestingModule({
      imports: [ValuationComponent],
      providers: [
        provideRouter([]),
        { provide: ValuationApiService, useValue: api },
        { provide: ToastrService, useValue: toastr },
      ],
    });
    const fixture = TestBed.createComponent(ValuationComponent);
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    const q = <T extends Element>(id: string) => el.querySelector<T>(`[data-testid="${id}"]`);
    const click = (id: string) => {
      q<HTMLButtonElement>(id)?.click();
      fixture.detectChanges();
    };
    const type = (input: HTMLInputElement, value: string) => {
      input.value = value;
      input.dispatchEvent(new Event('input'));
      fixture.detectChanges();
    };
    return { fixture, api, toastr, el, q, click, type, component: fixture.componentInstance };
  }

  it('starts on «Conciliar» with the reconciled quantities and the cost-of-management note (UI-02, UI-04)', () => {
    const { q, el } = create();
    expect(q('step-reconcile')).not.toBeNull();
    expect(q('method-note')?.textContent).toContain('no es una política fiscal ni contable');
    expect(el.textContent).toContain('Harina');
    expect(el.textContent).toContain('Central: 3');
  });

  it('blocks the wizard when the proposal has negative balances (AC-04, UI-06)', () => {
    const blocked: Proposal = {
      lines: [],
      blockers: [{ productId: 'p-2', productName: 'Azúcar', warehouseId: 'w-1', warehouseName: 'Central', quantity: '-1.0000' }],
    };
    const { q, el } = create({ proposal: blocked });
    expect(q('blockers')?.textContent).toContain('Azúcar en Central');
    expect(q<HTMLButtonElement>('to-values')?.disabled).toBeTrue();
    expect(el.textContent).not.toContain('Revisar resumen');
  });

  it('marks a line «Pendiente» and keeps «Revisar resumen» disabled until it has a value or zero is declared (UI-03)', () => {
    const { q, click, type, fixture } = create();
    click('to-values');
    expect(q('pending-badge')?.textContent).toContain('Pendiente');
    expect(q<HTMLButtonElement>('review')?.disabled).toBeTrue();
    expect(q('pending-note')).not.toBeNull();

    type(fixture.nativeElement.querySelector('input[inputmode="decimal"]'), '10.00');
    expect(q('pending-badge')).toBeNull();
    expect(q('unit-cost')?.textContent).toContain('3.333333');
    expect(q<HTMLButtonElement>('review')?.disabled).toBeFalse();
  });

  it('accepts an explicit zero cost and rejects an undeclared zero', () => {
    const { q, click, type, fixture } = create();
    click('to-values');
    type(fixture.nativeElement.querySelector('input[inputmode="decimal"]'), '0');
    expect(q('value-error')?.textContent).toContain('declararse explícitamente');
    expect(q<HTMLButtonElement>('review')?.disabled).toBeTrue();

    const zero = fixture.nativeElement.querySelector('input[type="checkbox"]') as HTMLInputElement;
    zero.click();
    fixture.detectChanges();
    expect(q<HTMLButtonElement>('review')?.disabled).toBeFalse();
    expect(q('unit-cost')?.textContent).toContain('0.000000');
  });

  it('shows the summary and confirms once with the sent values; then shows the adopted cut (AC-01, UI-05, UI-07)', () => {
    const { api, q, click, type, fixture, toastr } = create();
    click('to-values');
    type(fixture.nativeElement.querySelector('input[inputmode="decimal"]'), '10.00');
    click('review');
    expect(q('summary-count')?.textContent).toContain('1');
    expect(q('summary-total')?.textContent).toContain('Bs 10.00');
    click('confirm');
    const input = api.adopt.calls.mostRecent().args[0];
    expect(input.lines).toEqual([
      { productId: 'p-1', reconciledQuantity: '3.0000', totalValue: '10.00', declaredZero: false, source: '' },
    ]);
    expect(input.adoptionId).toMatch(/^[0-9a-f-]{36}$/);
    expect(toastr.success).toHaveBeenCalled();
    expect(q('adopted-success')?.textContent).toContain('Valoración adoptada');
    expect(q('adoption-summary')).not.toBeNull();
    expect(q('adopted-line')?.textContent).toContain('3.333333');
  });

  it('reloads the proposal and explains it when the stock changed (AC-05)', () => {
    const { api, q, click, type, fixture } = create({
      adopt: throwError(() => new ValuationApiError('cambió', 409, 'stock_changed')),
    });
    click('to-values');
    type(fixture.nativeElement.querySelector('input[inputmode="decimal"]'), '10.00');
    click('review');
    click('confirm');
    expect(api.proposal).toHaveBeenCalledTimes(2);
    expect(q('step-reconcile')).not.toBeNull();
    expect(q('valuation-conflict')?.textContent).toContain(STOCK_CHANGED_MESSAGE);
    expect(q<HTMLButtonElement>('to-values')?.disabled).toBeFalse();
  });

  it('shows server errors per line without losing what was typed (AC-03)', () => {
    const { q, click, type, fixture } = create({
      adopt: throwError(() => new ValuationApiError('Revisa', 400, null, [{ totalValue: ['Valor inválido del servidor'] }])),
    });
    click('to-values');
    const input = fixture.nativeElement.querySelector('input[inputmode="decimal"]') as HTMLInputElement;
    type(input, '10.00');
    click('review');
    click('confirm');
    expect(q('step-values')).not.toBeNull();
    expect(q('value-error')?.textContent).toContain('Valor inválido del servidor');
    expect((fixture.nativeElement.querySelector('input[inputmode="decimal"]') as HTMLInputElement).value).toBe('10.00');
  });

  it('shows negative-stock blockers returned by the server on confirm (AC-04)', () => {
    const blockers = [{ productId: 'p-1', productName: 'Harina', warehouseId: 'w-1', warehouseName: 'Central', quantity: '-1.0000' }];
    const { q, click, type, fixture } = create({
      adopt: throwError(() => new ValuationApiError('Stock negativo', 409, 'negative_stock', [], blockers)),
    });
    click('to-values');
    type(fixture.nativeElement.querySelector('input[inputmode="decimal"]'), '10.00');
    click('review');
    click('confirm');
    expect(q('blockers')?.textContent).toContain('Harina en Central');
    expect(q<HTMLButtonElement>('to-values')?.disabled).toBeTrue();
  });

  it('shows the read-only cut when already adopted, with search by name (UI-05)', () => {
    const { q, el, type, api } = create({ valuation: { status: 'adopted', adoption: ADOPTION } });
    expect(api.proposal).not.toHaveBeenCalled();
    expect(q('adopted-success')).toBeNull();
    expect(q('adoption-summary')?.textContent).toContain('Promedio ponderado móvil');
    expect(q('adopted-line')?.textContent).toContain('Bs 10.00');
    expect(el.querySelector('button[data-testid="confirm"]')).toBeNull();
    type(el.querySelector('#valuation-search') as HTMLInputElement, 'zzz');
    expect(q('adopted-empty')?.textContent).toContain('Sin resultados');
  });

  it('allows adopting with no stock (empty state, AC-07)', () => {
    const { q, click } = create({ proposal: { lines: [], blockers: [] } });
    expect(q('reconcile-empty')?.textContent).toContain('No hay existencias que valorar');
    click('to-values');
    expect(q<HTMLButtonElement>('review')?.disabled).toBeFalse();
  });

  it('shows an error with «Reintentar» when loading fails (estado error)', () => {
    const api = jasmine.createSpyObj<ValuationApiService>('ValuationApiService', ['get', 'proposal', 'adopt']);
    api.get.and.returnValue(throwError(() => new ValuationApiError('Sin conexión', 0)));
    TestBed.configureTestingModule({
      imports: [ValuationComponent],
      providers: [
        provideRouter([]),
        { provide: ValuationApiService, useValue: api },
        { provide: ToastrService, useValue: jasmine.createSpyObj<ToastrService>('ToastrService', ['success']) },
      ],
    });
    const fixture = TestBed.createComponent(ValuationComponent);
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('[data-testid="load-error"]')?.textContent).toContain('Sin conexión');
    expect(el.querySelector('[data-testid="retry"]')).not.toBeNull();
  });

  it('warns about unsaved values only while the wizard is being edited', () => {
    const { component, click, type, fixture } = create();
    click('to-values');
    expect(component.hasUnsavedChanges()).toBeFalse();
    const input = fixture.nativeElement.querySelector('input[inputmode="decimal"]') as HTMLInputElement;
    input.value = '5';
    input.dispatchEvent(new Event('input'));
    fixture.detectChanges();
    expect(component.hasUnsavedChanges()).toBeTrue();
    type(input, '5');
  });
});
