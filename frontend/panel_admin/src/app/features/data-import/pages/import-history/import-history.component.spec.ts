import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { Observable, of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { Page } from '../../../../shared/models/page';
import { ImportApiError, ImportRunSummary } from '../../models/sales-import';
import { SalesImportApiService } from '../../services/sales-import-api.service';
import { RUN } from '../../testing/import-fixtures';
import { ImportHistoryComponent } from './import-history.component';

describe('ImportHistoryComponent', () => {
  function create(response: Observable<Page<ImportRunSummary>>) {
    const api = jasmine.createSpyObj<SalesImportApiService>('SalesImportApiService', ['list']);
    api.list.and.returnValue(response);
    TestBed.configureTestingModule({
      imports: [ImportHistoryComponent],
      providers: [...provideTestTranslations(), provideRouter([]), { provide: SalesImportApiService, useValue: api }],
    });
    const fixture = TestBed.createComponent(ImportHistoryComponent);
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    const q = (id: string) => el.querySelector<HTMLElement>(`[data-testid="${id}"]`);
    return { fixture, api, el, q };
  }

  it('shows the loading state first', () => {
    const { q } = create(new Observable<Page<ImportRunSummary>>());
    expect(q('loading')).not.toBeNull();
  });

  it('shows the empty message', () => {
    const { q } = create(of({ count: 0, next: null, previous: null, results: [] }));
    expect(q('empty')?.textContent).toContain('Aún no se ha importado ningún archivo.');
  });

  it('lists the runs with status badge text, counts and a detail link', () => {
    const { q, el } = create(of({ count: 1, next: null, previous: null, results: [RUN] }));
    const row = q('history-row')!;
    expect(row.textContent).toContain('ventas.csv');
    expect(row.textContent).toContain('ana');
    expect(row.textContent).toContain('Completada');
    expect(row.textContent).toContain('2 / 0');
    expect(q('detail-link')?.getAttribute('href')).toBe('/pocketbiz/sales/import/history/run-1');
    expect(el.querySelector('ngb-pagination')).toBeNull();
  });

  it('shows the error with a retry that reloads', () => {
    const { api, q, fixture } = create(throwError(() => new ImportApiError('Sin conexión', 0)));
    expect(q('load-error')?.textContent).toContain('Sin conexión');
    api.list.and.returnValue(of({ count: 0, next: null, previous: null, results: [] }));
    q('retry')!.click();
    fixture.detectChanges();
    expect(api.list).toHaveBeenCalledTimes(2);
    expect(q('empty')).not.toBeNull();
  });
});
