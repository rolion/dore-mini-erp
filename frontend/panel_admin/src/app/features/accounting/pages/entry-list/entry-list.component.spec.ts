import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { BehaviorSubject, of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { AccountingApiError } from '../../models/accounting';
import { makeEntry, makeEntryPage } from '../../testing/entry-fixtures';
import { AccountingApiService } from '../../services/accounting-api.service';
import { EntriesApiService } from '../../services/entries-api.service';
import { EntryListComponent } from './entry-list.component';

describe('EntryListComponent', () => {
  let fixture: ComponentFixture<EntryListComponent>;
  let component: EntryListComponent;
  let api: jasmine.SpyObj<EntriesApiService>;
  let router: Router;

  async function setup(params: Record<string, string> = {}, page = makeEntryPage()): Promise<void> {
    api = jasmine.createSpyObj<EntriesApiService>('EntriesApiService', ['list']);
    api.list.and.returnValue(of(page));
    const accounting = jasmine.createSpyObj<AccountingApiService>('AccountingApiService', ['listAccounts', 'listMethods']);
    accounting.listAccounts.and.returnValue(of([{ id: 'a-1', name: 'Caja', currency: 'BOB', isActive: true }]));
    accounting.listMethods.and.returnValue(of([{ code: 'CASH', label: 'Efectivo', isActive: true, account: null }]));
    await TestBed.configureTestingModule({
      imports: [EntryListComponent],
      providers: [
        ...provideTestTranslations(),
        provideRouter([]),
        { provide: EntriesApiService, useValue: api },
        { provide: AccountingApiService, useValue: accounting },
        { provide: ActivatedRoute, useValue: { queryParamMap: new BehaviorSubject(convertToParamMap(params)).asObservable() } },
      ],
    }).compileComponents();
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    fixture = TestBed.createComponent(EntryListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  }

  const root = (): HTMLElement => fixture.nativeElement as HTMLElement;
  const byId = (id: string): HTMLElement | null => root().querySelector(`[data-testid="${id}"]`);

  it('shows rows, totals per currency, period, coverage and the context note (UI-02, UI-03)', async () => {
    await setup();
    expect(api.list).toHaveBeenCalledWith(jasmine.objectContaining({ page: 1, pageSize: 20 }));
    expect(root().querySelectorAll('datatable-body-row').length).toBe(1);
    expect(byId('total-amount')?.textContent).toContain('300.50');
    expect(byId('coverage')).not.toBeNull();
    expect(byId('context-note')).not.toBeNull();
    expect(byId('period')?.textContent).toContain('Todas las fechas');
  });

  it('shows one totals row per currency without mixing them', async () => {
    const page = makeEntryPage([makeEntry()], {
      totals: [
        { currency: 'BOB', count: 2, amount: '550.50', byOrigin: { PRODUCT: '250.00', SERVICE: '300.50' } },
        { currency: 'USD', count: 1, amount: '70.00', byOrigin: { PRODUCT: '70.00', SERVICE: '0.00' } },
      ],
    });
    await setup({}, page);
    const rows = Array.from(root().querySelectorAll('[data-testid="total-row"]')).map((r) => r.textContent ?? '');
    expect(rows.length).toBe(2);
    expect(rows[1]).toContain('70.00 USD');
  });

  it('reads the filters from the URL and sends them to the API', async () => {
    await setup({ date_from: '2026-11-01', origin: 'SERVICE', method: 'CASH', account_id: 'a-1' });
    expect(api.list).toHaveBeenCalledWith(jasmine.objectContaining({ dateFrom: '2026-11-01', origin: 'SERVICE', method: 'CASH', accountId: 'a-1' }));
    expect(component.filtersActive).toBeTrue();
  });

  it('writes the form into the URL and does not query with an inverted range', async () => {
    await setup();
    component.filterForm.patchValue({ origin: 'PRODUCT' });
    component.applyForm();
    expect(router.navigate).toHaveBeenCalledWith(['/pocketbiz/accounting/entries'], { queryParams: { origin: 'PRODUCT' } });
    (router.navigate as jasmine.Spy).calls.reset();
    component.filterForm.patchValue({ dateFrom: '2026-12-01', dateTo: '2026-11-01' });
    component.applyForm();
    fixture.detectChanges();
    expect(router.navigate).not.toHaveBeenCalled();
    expect(byId('range-error')).not.toBeNull();
  });

  it('shows the empty book message without filters and the applied filters when filtering (UI-02)', async () => {
    await setup({}, makeEntryPage([]));
    expect(byId('empty-book')).not.toBeNull();
    expect(byId('totals-empty')).not.toBeNull();
    TestBed.resetTestingModule();
    await setup({ origin: 'SERVICE' }, makeEntryPage([]));
    expect(byId('empty-filtered')).not.toBeNull();
    expect(root().querySelectorAll('[data-testid="applied-filter"]').length).toBe(1);
  });

  it('shows the server error with a retry action', async () => {
    await setup();
    api.list.and.returnValue(throwError(() => new AccountingApiError('Falló', 500)));
    component.retry();
    fixture.detectChanges();
    expect(byId('list-error')?.textContent).toContain('Falló');
    api.list.and.returnValue(of(makeEntryPage()));
    (byId('retry') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(byId('list-error')).toBeNull();
  });

  it('links to the document only when it is available, and offers no write actions (UI-04)', async () => {
    await setup({}, makeEntryPage([makeEntry({ documentRef: 'o-1' }), makeEntry({ id: 'e-2', sourceAvailable: false })]));
    expect(root().querySelectorAll('[data-testid="source-link"]').length).toBe(1);
    expect(root().querySelectorAll('[data-testid="source-text"]').length).toBe(1);
    expect(root().querySelector('a[href$="/new"], .btn-tbl-update, .btn-tbl-delete')).toBeNull();
  });
});
