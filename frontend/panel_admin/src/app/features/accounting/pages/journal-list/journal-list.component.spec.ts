import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { BehaviorSubject, of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { AccountingApiError } from '../../models/accounting';
import { JournalPage } from '../../models/journal';
import { AccountingApiService } from '../../services/accounting-api.service';
import { JournalApiService } from '../../services/journal-api.service';
import { JournalFiltersState } from '../../services/journal-filters-state';
import { makeJournalRow } from '../../testing/journal-fixtures';
import { JournalListComponent, journalFiltersFromParams, journalFiltersToQuery } from './journal-list.component';

describe('JournalListComponent', () => {
  function create(page: JournalPage | Error, query: Record<string, string> = {}) {
    const journal = jasmine.createSpyObj<JournalApiService>('JournalApiService', ['list']);
    journal.list.and.returnValue(page instanceof Error ? throwError(() => page) : of(page));
    const accounting = jasmine.createSpyObj<AccountingApiService>('AccountingApiService', ['listAccounts']);
    accounting.listAccounts.and.returnValue(of([]));
    const params = new BehaviorSubject(convertToParamMap(query));
    TestBed.configureTestingModule({
      imports: [JournalListComponent],
      providers: [
        ...provideTestTranslations(), provideRouter([]),
        { provide: JournalApiService, useValue: journal },
        { provide: AccountingApiService, useValue: accounting },
        { provide: ActivatedRoute, useValue: { queryParamMap: params, snapshot: { queryParamMap: convertToParamMap(query) } } },
      ],
    });
    const fixture = TestBed.createComponent(JournalListComponent);
    fixture.detectChanges();
    return { fixture, journal, el: fixture.nativeElement as HTMLElement };
  }

  it('lists entries and reads filters and page from the URL (AC-03)', () => {
    const { journal, el } = create(
      { count: 1, results: [makeJournalRow({ description: 'Venta mostrador' })] },
      { date_from: '2026-05-01', source: 'MANUAL', account_id: 'a-1', page: '2' },
    );
    expect(journal.list).toHaveBeenCalledWith(jasmine.objectContaining({ dateFrom: '2026-05-01', source: 'MANUAL', accountId: 'a-1', page: 2, pageSize: 20 }));
    expect(el.textContent).toContain('Venta mostrador');
    expect(el.querySelector('[data-testid="new-entry"]')).not.toBeNull();
    expect(el.querySelector('.btn-danger')).toBeNull(); // sin editar ni borrar
  });

  it('ignores an unknown source and an invalid page', () => {
    expect(journalFiltersFromParams(convertToParamMap({ source: 'X' })).source).toBe('');
    expect(journalFiltersToQuery({ dateFrom: '', dateTo: '', accountId: '', source: '' }, 0)).toEqual({});
    expect(journalFiltersToQuery({ dateFrom: '2026-05-01', dateTo: '', accountId: '', source: 'AUTOMATIC' }, 2)).toEqual({ date_from: '2026-05-01', source: 'AUTOMATIC', page: 3 });
  });

  it('shows the empty book with an action to create the first entry', () => {
    const { el } = create({ count: 0, results: [] });
    expect(el.querySelector('[data-testid="empty-book"]')).not.toBeNull();
    expect(el.querySelector('[data-testid="empty-filtered"]')).toBeNull();
  });

  it('shows the filtered empty state with the applied filters and a way to clear them', () => {
    const { el } = create({ count: 0, results: [] }, { source: 'AUTOMATIC' });
    expect(el.querySelector('[data-testid="empty-filtered"]')).not.toBeNull();
    expect(el.querySelectorAll('[data-testid="applied-filter"]').length).toBe(1);
  });

  it('shows a server error with retry', () => {
    const { el, journal } = create(new AccountingApiError('Falló', 500));
    expect(el.querySelector('[data-testid="list-error"]')?.textContent).toContain('Falló');
    (el.querySelector('[data-testid="retry"]') as HTMLButtonElement).click();
    expect(journal.list).toHaveBeenCalledTimes(2);
  });

  it('remembers the filters to restore them when coming back from a detail (AC-03)', () => {
    create({ count: 0, results: [] }, { source: 'MANUAL', page: '3' });
    const state = TestBed.inject(JournalFiltersState);
    expect([state.filters.source, state.pageIndex]).toEqual(['MANUAL', 2]);
  });

  it('puts the filters in the URL when the form changes', () => {
    const { fixture } = create({ count: 0, results: [] });
    const navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
    fixture.componentInstance.filterForm.patchValue({ source: 'MANUAL' }, { emitEvent: false });
    fixture.componentInstance.applyForm();
    expect(navigate).toHaveBeenCalledWith(['/pocketbiz/accounting/journal'], { queryParams: { source: 'MANUAL' } });
    fixture.componentInstance.filterForm.patchValue({ dateFrom: '2026-06-01', dateTo: '2026-05-01' }, { emitEvent: false });
    navigate.calls.reset();
    fixture.componentInstance.applyForm();
    expect(fixture.componentInstance.rangeInvalid).toBeTrue();
    expect(navigate).not.toHaveBeenCalled();
  });
});
