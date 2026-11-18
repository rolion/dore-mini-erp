import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { Observable, of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { AccountingApiError } from '../../models/accounting';
import { Entry } from '../../models/entry';
import { makeEntry } from '../../testing/entry-fixtures';
import { EntriesApiService } from '../../services/entries-api.service';
import { EntryDetailComponent } from './entry-detail.component';

describe('EntryDetailComponent', () => {
  function create(get: Observable<Entry>) {
    const api = jasmine.createSpyObj<EntriesApiService>('EntriesApiService', ['get']);
    api.get.and.returnValue(get);
    TestBed.configureTestingModule({
      imports: [EntryDetailComponent],
      providers: [
        ...provideTestTranslations(),
        provideRouter([]),
        { provide: EntriesApiService, useValue: api },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: 'e-1' }) } } },
      ],
    });
    const fixture = TestBed.createComponent(EntryDetailComponent);
    fixture.detectChanges();
    return { fixture, api };
  }

  it('shows classification, signed amount and links between a movement and its reversal (UI-02, UI-04)', () => {
    const original = create(of(makeEntry({
      origin: 'EXPENSE', direction: 'EXPENSE', classificationName: 'Alquiler', reversedBy: 'e-9', documentRef: 'gasto-1',
    }))).fixture.nativeElement as HTMLElement;
    expect(original.querySelector('[data-testid="amount"]')?.textContent).toContain('−');
    expect(original.querySelector('[data-testid="classification"]')?.textContent).toContain('Alquiler');
    expect(original.querySelector('[data-testid="reversal-link"]')).not.toBeNull();
    expect(original.querySelector('[data-testid="reversal-badge"]')).toBeNull();
    TestBed.resetTestingModule();
    const reversal = create(of(makeEntry({ operation: 'REVERSAL', direction: 'INCOME', reversalOf: 'e-1' }))).fixture
      .nativeElement as HTMLElement;
    expect(reversal.querySelector('[data-testid="reversal-badge"]')).not.toBeNull();
    expect(reversal.querySelector('[data-testid="original-link"]')).not.toBeNull();
  });

  it('shows the entry data with a link to the source and no edit actions (UI-04)', () => {
    const { fixture, api } = create(of(makeEntry({ documentRef: 'o-1', receiptNumber: 'CB-000001' })));
    const el = fixture.nativeElement as HTMLElement;
    expect(api.get).toHaveBeenCalledWith('e-1');
    expect(el.querySelector('[data-testid="amount"]')?.textContent).toContain('300.50');
    expect(el.querySelector('[data-testid="source-link"]')).not.toBeNull();
    expect(el.querySelector('[data-testid="source-link"]')?.getAttribute('aria-label')).toContain('o-1');
    expect(el.textContent).toContain('CB-000001');
    expect(el.querySelector('.btn-danger, .btn-warning')).toBeNull();
    expect(el.querySelector('[data-testid="view-source"]')?.textContent).toContain('Ver pedido');
  });

  it('shows the receipt as text and offers no "Ver cobro" for services (link deferred, REV-06)', () => {
    const { fixture } = create(of(makeEntry({ origin: 'SERVICE', documentRef: 'quotation/PRO-1', receiptNumber: 'CB-000002' })));
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('[data-testid="receipt-link"]')).toBeNull();
    expect(el.querySelector('[data-testid="view-source"]')).toBeNull();
    expect(el.textContent).toContain('CB-000002');
  });

  it('shows plain text when the source module is disabled', () => {
    const { fixture } = create(of(makeEntry({ sourceAvailable: false, documentRef: 'o-1' })));
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('[data-testid="source-link"]')).toBeNull();
    expect(el.querySelector('[data-testid="source-text"]')?.textContent).toContain('módulo deshabilitado');
  });

  it('shows the error and offers retry unless the entry does not exist', () => {
    const { fixture } = create(throwError(() => new AccountingApiError('Sin conexión', 0)));
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('[data-testid="detail-error"]')?.textContent).toContain('Sin conexión');
    expect(el.querySelector('[data-testid="retry"]')).not.toBeNull();
    TestBed.resetTestingModule();
    const missing = create(throwError(() => new AccountingApiError('No existe', 404)));
    expect((missing.fixture.nativeElement as HTMLElement).querySelector('[data-testid="retry"]')).toBeNull();
  });
});
