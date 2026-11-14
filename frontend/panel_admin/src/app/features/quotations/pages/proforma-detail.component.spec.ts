import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { BehaviorSubject, of } from 'rxjs';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { ModulesService } from '../../../core/service/modules.service';
import { Commitment } from '../../../shared/models/receivable';
import { Proforma } from '../models/proforma';
import { ProformaDetailComponent } from './proforma-detail.component';

const PROFORMA: Proforma = {
  id: 'p1', number: 'PRO-000001', version: 1, status: 'presented', customer_id: 'c1', customer_name: 'Rosa Pérez',
  date: '2026-11-04', valid_until: null, currency: 'BOB', total: '250.00', accepted_total: '250.00',
  acceptance_status: 'accepted', collectible: true, notes: '', can_edit_price: false, allowed_actions: [],
  lines: [{ id: 'l1', service_id: 's1', description: 'Limpieza', quantity: '1.00', unit_price: '250.00', subtotal: '250.00',
    treatment_item_id: null, piece: '', line_kind: 'original', origin_line_id: null, decision: 'accepted',
    decided_at: '2026-11-04T10:00:00Z', decision_detail: null, authorized: true }],
  versions: [], decision_actions: [], totals: { proposed: '250.00', accepted: '250.00', pending: '0.00', rejected: '0.00' },
  decision_history: [], previous_version_id: null,
};

const COMMITMENT = (balance: string): Commitment => ({
  kind: 'quotation', number: 'PRO-000001', version: 1, status: 'presented', customer_id: 'c1', proforma_id: 'p1',
  customer_name: 'Rosa Pérez', date: '2026-11-04', currency: 'BOB', payment_status: 'pending',
  totals: { proposed: '250.00', accepted: '250.00', pending: '0.00', rejected: '0.00', paid: '0.00', balance },
  lines: [], payments: [], allowed_actions: ['register_payment'],
});

describe('ProformaDetailComponent (cobro en contexto)', () => {
  let http: HttpTestingController;

  function create(enabled: string[]) {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([]), ...provideTestTranslations(),
        { provide: ModulesService, useValue: { enabledKeys$: new BehaviorSubject<ReadonlySet<string> | null>(new Set(enabled)) } },
        { provide: ActivatedRoute, useValue: { paramMap: of(convertToParamMap({ id: 'p1' })) } }],
    });
    http = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(ProformaDetailComponent);
    fixture.detectChanges();
    http.expectOne((req) => req.url.endsWith('/quotations/proformas/p1/')).flush(PROFORMA);
    fixture.detectChanges();
    return fixture;
  }

  afterEach(() => http.verify());

  it('con Cobros habilitado y saldo pendiente ofrece «Cobrar», que abre el diálogo en la misma página (AC-07)', () => {
    const fixture = create(['receivables']);
    http.expectOne((req) => req.url.endsWith('/receivables/commitments/quotation/PRO-000001/')).flush(COMMITMENT('250.00'));
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    const button = Array.from(root.querySelectorAll<HTMLButtonElement>('.card-header button')).find((b) => b.textContent?.trim() === 'Cobrar');
    expect(button).toBeDefined();
    expect(root.textContent).toContain('Saldo por cobrar'); // AC-08
    button?.click();
    http.expectOne((req) => req.url.endsWith('/receivables/commitments/quotation/PRO-000001/')).flush(COMMITMENT('250.00'));
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('sin saldo por cobrar no ofrece cobrar', () => {
    const fixture = create(['receivables']);
    http.expectOne((req) => req.url.endsWith('/receivables/commitments/quotation/PRO-000001/')).flush(COMMITMENT('0.00'));
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    expect(Array.from(root.querySelectorAll('.card-header button')).some((b) => b.textContent?.trim() === 'Cobrar')).toBeFalse();
  });

  it('sin el módulo Cobros no hay botón ni lecturas de cobro', () => {
    const fixture = create([]);
    http.expectNone((req) => req.url.includes('/receivables/'));
    expect((fixture.nativeElement as HTMLElement).textContent).not.toContain('Cobrar');
  });
});
