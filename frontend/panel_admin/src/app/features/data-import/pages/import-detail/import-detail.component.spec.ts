import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { Observable, of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { ImportApiError, ImportRunDetail } from '../../models/sales-import';
import { SalesImportApiService } from '../../services/sales-import-api.service';
import { ROWS, RUN } from '../../testing/import-fixtures';
import { ImportDetailComponent } from './import-detail.component';

describe('ImportDetailComponent', () => {
  function create(run: Observable<ImportRunDetail>) {
    const api = jasmine.createSpyObj<SalesImportApiService>('SalesImportApiService', ['get', 'rows']);
    api.get.and.returnValue(run);
    api.rows.and.returnValue(of({ count: ROWS.length, next: null, previous: null, results: ROWS }));
    TestBed.configureTestingModule({
      imports: [ImportDetailComponent],
      providers: [
        ...provideTestTranslations(),
        provideRouter([]),
        { provide: SalesImportApiService, useValue: api },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: 'run-1' }) } } },
      ],
    });
    const fixture = TestBed.createComponent(ImportDetailComponent);
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    const q = (id: string) => el.querySelector<HTMLElement>(`[data-testid="${id}"]`);
    return { fixture, api, el, q };
  }

  it('shows loading, then the run summary, counts and rows with text badges', () => {
    const loading = create(new Observable<ImportRunDetail>());
    expect(loading.q('loading')).not.toBeNull();
    TestBed.resetTestingModule();

    const { api, q, el } = create(of(RUN));
    expect(api.get).toHaveBeenCalledWith('run-1');
    expect(q('run-file')?.textContent).toContain('ventas.csv');
    expect(q('count-created')?.textContent).toContain('2');
    expect(el.querySelectorAll('[data-testid="import-row"]').length).toBe(4);
    for (const label of ['Cargada', 'Ya importada', 'Cargada sin asiento', 'Con error']) {
      expect(el.textContent).toContain(label);
    }
  });

  it('filters the rows by status', () => {
    const { api, q, fixture } = create(of(RUN));
    const select = q('rows-status-filter') as HTMLSelectElement;
    select.value = 'FAILED';
    select.dispatchEvent(new Event('change'));
    fixture.detectChanges();
    expect(api.rows.calls.mostRecent().args).toEqual(['run-1', 'FAILED', 1]);
  });

  it('shows a not-found error with retry', () => {
    const { q } = create(throwError(() => new ImportApiError('Importación no encontrada.', 404)));
    expect(q('load-error')?.textContent).toContain('Importación no encontrada.');
    expect(q('retry')).not.toBeNull();
  });
});
