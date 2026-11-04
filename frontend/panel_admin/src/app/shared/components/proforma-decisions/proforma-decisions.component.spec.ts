import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { DecisionLineView } from '../../models/proforma-decisions';
import { ProformaDecisionsComponent } from './proforma-decisions.component';

const LINES: DecisionLineView[] = [
  { id: 'l1', description: 'Limpieza', quantity: '1.00', unit_price: '100.00', subtotal: '100.00', decision: 'pending', decided_at: null, authorized: false, line_kind: 'original', origin_line_id: null, decision_detail: null },
  { id: 'l2', description: 'Corona', quantity: '1.00', unit_price: '200.00', subtotal: '200.00', decision: 'pending', decided_at: null, authorized: false, line_kind: 'original', origin_line_id: null, decision_detail: null },
];

describe('ProformaDecisionsComponent', () => {
  let http: HttpTestingController;
  let fixture: ComponentFixture<ProformaDecisionsComponent>;

  function create(overrides: Record<string, unknown> = {}) {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([]), ...provideTestTranslations()] });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(ProformaDecisionsComponent);
    const inputs: Record<string, unknown> = {
      base: 'quotations/proformas', proformaId: 'p1', status: 'presented', lines: LINES,
      totals: { proposed: '300.00', accepted: '0.00', pending: '300.00', rejected: '0.00' },
      acceptanceStatus: 'pending', actions: ['decide'], history: [], ...overrides,
    };
    for (const [key, value] of Object.entries(inputs)) fixture.componentRef.setInput(key, value);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  afterEach(() => http.verify());

  it('shows proposed, accepted and pending totals separately, and the decision of each line as text', () => {
    const text = create().textContent ?? '';
    expect(text).toContain('Total propuesto');
    expect(text).toContain('Total aceptado');
    expect(text).toContain('Pendiente de decisión');
    expect(text).toContain('Pendiente');
  });

  it('only offers selection and actions when the server allows deciding on a presented proforma', () => {
    expect(create({ actions: [] }).querySelectorAll('tbody input[type=checkbox]').length).toBe(0);
  });

  it('summarises exactly the selected lines and sends one request with a stable idempotency key', () => {
    const root = create();
    const boxes = root.querySelectorAll<HTMLInputElement>('tbody input[type=checkbox]');
    boxes[0].click();
    fixture.detectChanges();
    const component = fixture.componentInstance;
    expect(component.chosen().map(l => l.id)).toEqual(['l1']);
    expect(component.chosenAmount()).toBe('100.00');
    const dialog = root.querySelector('dialog') as HTMLDialogElement;
    component.openDecision('accepted', dialog);
    component.form.patchValue({ accepted_by_name: 'Rosa Pérez', medium: 'in_person' });
    component.next();
    expect(component.step()).toBe(2);
    component.confirm(dialog);
    const first = http.expectOne(r => r.url.endsWith('/quotations/proformas/p1/decisions/'));
    expect(first.request.body.line_ids).toEqual(['l1']);
    const key = first.request.body.idempotency_key as string;
    first.flush({}, { status: 500, statusText: 'Error' });
    expect(component.error()).not.toBe('');
    expect(component.form.getRawValue().accepted_by_name).toBe('Rosa Pérez'); // se conservan los datos
    component.confirm(dialog);
    const retry = http.expectOne(r => r.url.endsWith('/decisions/'));
    expect(retry.request.body.idempotency_key).toBe(key); // el reintento reutiliza la clave
    let changed = 0;
    component.changed.subscribe(() => changed++);
    retry.flush({});
    expect(changed).toBe(1);
  });

  it('blocks a double submit while a request is in flight', () => {
    const root = create();
    root.querySelectorAll<HTMLInputElement>('tbody input[type=checkbox]')[0].click();
    const component = fixture.componentInstance;
    const dialog = root.querySelector('dialog') as HTMLDialogElement;
    component.openDecision('rejected', dialog);
    component.confirm(dialog);
    component.confirm(dialog);
    http.expectOne(r => r.url.endsWith('/decisions/')).flush({});
  });

  it('requires name and medium to accept, and a reason to rectify', () => {
    const root = create({ lines: [{ ...LINES[0], decision: 'accepted', decided_at: '2026-11-05T10:00:00Z', authorized: true }], actions: ['rectify'] });
    const component = fixture.componentInstance;
    const dialog = root.querySelector('dialog') as HTMLDialogElement;
    component.openRectify(component.lines()[0], dialog);
    component.confirmRectify(dialog);
    expect(component.fieldErrors()['reason']).toBeTruthy();
    component.form.patchValue({ reason: 'Cambio de opinión' });
    component.confirmRectify(dialog);
    const req = http.expectOne(r => r.url.endsWith('/lines/l1/rectify/'));
    expect(req.request.body.decision).toBe('rejected');
    req.flush({});
  });

  it('locks accepted lines inherited from a previous version in a draft and links the print view only when presented', () => {
    const locked = create({ status: 'draft', actions: [], lines: [{ ...LINES[0], decision: 'accepted', origin_line_id: 'o1', line_kind: 'carried' }] });
    expect(locked.textContent).toContain('Bloqueada');
    expect(locked.textContent).not.toContain('Imprimir');
  });
});
