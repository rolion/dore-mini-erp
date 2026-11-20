import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { NgbModal, NgbModalRef } from '@ng-bootstrap/ng-bootstrap';
import { Observable, of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { Page } from '../../../../shared/models/page';
import { ImportApiError, ImportResult, ImportRow, ImportUpload } from '../../models/sales-import';
import { SalesImportApiService } from '../../services/sales-import-api.service';
import { COUNTS, FULL_MAPPING, PREVIEW, ROWS, makeUpload } from '../../testing/import-fixtures';
import { SalesImportComponent } from './sales-import.component';

const RESULT: ImportResult = { id: 'run-1', status: 'COMPLETED', counts: COUNTS };

describe('SalesImportComponent', () => {
  function create(options: { upload?: ImportUpload; execute?: Observable<ImportResult> } = {}) {
    const api = jasmine.createSpyObj<SalesImportApiService>('SalesImportApiService', [
      'upload', 'preview', 'execute', 'get', 'rows', 'template', 'list',
    ]);
    api.upload.and.returnValue(of(options.upload ?? makeUpload()));
    api.preview.and.returnValue(of(PREVIEW));
    api.execute.and.returnValue(options.execute ?? of(RESULT));
    const rowsPage: Page<ImportRow> = { count: ROWS.length, next: null, previous: null, results: ROWS };
    api.rows.and.returnValue(of(rowsPage));
    const modal = jasmine.createSpyObj<NgbModal>('NgbModal', ['open']);
    modal.open.and.callFake(() => ({ componentInstance: {}, result: Promise.resolve(true) }) as unknown as NgbModalRef);
    TestBed.configureTestingModule({
      imports: [SalesImportComponent],
      providers: [
        ...provideTestTranslations(),
        provideRouter([]),
        { provide: SalesImportApiService, useValue: api },
        { provide: NgbModal, useValue: modal },
      ],
    });
    const fixture = TestBed.createComponent(SalesImportComponent);
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    const q = <T extends Element>(id: string) => el.querySelector<T>(`[data-testid="${id}"]`);
    const click = (id: string) => {
      q<HTMLButtonElement>(id)?.click();
      fixture.detectChanges();
    };
    const component = fixture.componentInstance;
    const toMapStep = () => {
      component.selectedFile = new File(['a'], 'ventas.csv');
      fixture.detectChanges();
      click('upload');
    };
    const toPreviewStep = () => {
      toMapStep();
      click('review');
    };
    return { fixture, api, modal, el, q, click, component, toMapStep, toPreviewStep };
  }

  it('starts on step 1 with the upload disabled until a file is chosen', () => {
    const { q, el } = create();
    expect(q('step-upload')).not.toBeNull();
    expect(q<HTMLButtonElement>('upload')!.disabled).toBeTrue();
    expect(q('step-indicator-1')?.getAttribute('aria-current')).toBe('step');
    expect(el.textContent).toContain('Máximo 5 MB y 2000 filas.');
  });

  it('shows the server error under the upload zone', () => {
    const { api, q, click, component, fixture } = create();
    api.upload.and.returnValue(throwError(() => new ImportApiError('Archivo vacío', 400, '', { file: ['Archivo vacío'] })));
    component.selectedFile = new File([''], 'x.csv');
    fixture.detectChanges();
    click('upload');
    expect(q('upload-error')?.textContent).toContain('Archivo vacío');
    expect(q('step-upload')).not.toBeNull();
  });

  it('moves to «Mapear» with the four checkboxes above the mapping, all checked when available', () => {
    const { q, el, toMapStep, component } = create();
    toMapStep();
    expect(component.step).toBe(2);
    for (const id of ['opt-products', 'opt-customers', 'opt-inventory', 'opt-accounting']) {
      const box = q<HTMLInputElement>(id)!;
      expect(box.checked).withContext(id).toBeTrue();
      expect(box.disabled).withContext(id).toBeFalse();
    }
    const boxes = q('opt-products')!;
    const table = q('mapping-table')!;
    expect(boxes.compareDocumentPosition(table) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(el.textContent).toContain('Cada venta se registra entregada y cobrada al total en su fecha.');
    expect((q<HTMLSelectElement>('default-payment')!).value).toBe('CASH');
    expect((q<HTMLSelectElement>('default-channel')!).value).toBe('OTHER');
    expect((q<HTMLSelectElement>('default-warehouse')!).value).toBe('w-1');
  });

  it('disables the checkboxes of unavailable modules with the reason in text', () => {
    const { q, toMapStep } = create({ upload: makeUpload({ customers: false, purchases: false, accounting: false }) });
    toMapStep();
    expect(q<HTMLInputElement>('opt-customers')!.disabled).toBeTrue();
    expect(q<HTMLInputElement>('opt-customers')!.checked).toBeFalse();
    expect(q('reason-customers')?.textContent).toContain('Clientes');
    expect(q<HTMLInputElement>('opt-inventory')!.disabled).toBeTrue();
    expect(q('reason-inventory')?.textContent).toContain('Inventario y Compras');
    expect(q<HTMLInputElement>('opt-accounting')!.disabled).toBeTrue();
    expect(q('reason-accounting')?.textContent).toContain('Contabilidad');
    expect(q<HTMLInputElement>('opt-products')!.disabled).toBeFalse();
  });

  it('hides the warehouse default without Inventory', () => {
    const { q, toMapStep } = create({ upload: makeUpload({ inventory: false }) });
    toMapStep();
    expect(q('default-warehouse')).toBeNull();
  });

  it('disables «Revisar» while a required field is unmapped', () => {
    const { q, toMapStep, component, fixture } = create({
      upload: makeUpload({}, { ...FULL_MAPPING, unit_price: null }),
    });
    toMapStep();
    expect(q<HTMLButtonElement>('review')!.disabled).toBeTrue();
    expect(q('missing-required')).not.toBeNull();
    component.mapping.controls.unit_price.setValue('Precio');
    fixture.detectChanges();
    expect(q<HTMLButtonElement>('review')!.disabled).toBeFalse();
  });

  it('previews with the mapping and options and shows the headline and the problem rows', () => {
    const { api, q, toPreviewStep, component, el } = create();
    toPreviewStep();
    expect(component.step).toBe(3);
    const [id, request] = api.preview.calls.mostRecent().args;
    expect(id).toBe('run-1');
    expect(request.mapping.sale_date).toBe('Fecha');
    expect(request.mapping.notes).toBeNull();
    expect(request.options.inferInventory).toBeTrue();
    expect(request.options.warehouseId).toBe('w-1');
    expect(q('preview-note')?.textContent).toContain('No se ha escrito nada');
    expect(q('preview-headline')?.textContent).toContain('2 se cargarían');
    expect(q('problem-row')?.textContent).toContain('Cantidad inválida');
    expect(el.textContent).toContain('Productos nuevos: 1');
  });

  it('keeps the user on step 2 with the messages when the preview returns 400', () => {
    const { api, q, toMapStep, click, component } = create();
    api.preview.and.returnValue(throwError(() => new ImportApiError('x', 400, '', { mapping: ['Falta la columna Precio'] })));
    toMapStep();
    click('review');
    expect(component.step).toBe(2);
    expect(q('preview-error')?.textContent).toContain('Falta la columna Precio');
  });

  it('disables «Cargar ventas» when the mapping changed after the preview', () => {
    const { q, toPreviewStep, component, fixture } = create();
    toPreviewStep();
    expect(q<HTMLButtonElement>('execute')!.disabled).toBeFalse();
    component.mapping.controls.quantity.setValue('Precio');
    fixture.detectChanges();
    expect(q<HTMLButtonElement>('execute')!.disabled).toBeTrue();
    expect(q('stale-warning')).not.toBeNull();
  });

  it('confirms in a static modal and goes to the result', async () => {
    const { api, modal, q, toPreviewStep, click, component, fixture } = create();
    toPreviewStep();
    click('execute');
    expect(modal.open.calls.mostRecent().args[1]).toEqual(jasmine.objectContaining({ backdrop: 'static', keyboard: false }));
    await fixture.whenStable();
    fixture.detectChanges();
    expect(api.execute).toHaveBeenCalledTimes(1);
    expect(component.step).toBe(4);
    expect(q('result-alert')?.textContent).toContain('Importación completada');
    expect(q('count-created')?.textContent).toContain('2');
    expect(q('count-skipped')?.textContent).toContain('1');
    expect(fixture.nativeElement.textContent).toContain('Cargada sin asiento');
    expect(fixture.nativeElement.textContent).toContain('Con error');
    expect(q('order-link')).not.toBeNull();
  });

  it('reuses the same idempotency key when the load is retried', async () => {
    const { api, q, toPreviewStep, click, fixture } = create();
    api.execute.and.returnValues(throwError(() => new ImportApiError('Falla', 500)), of(RESULT));
    toPreviewStep();
    click('execute');
    await fixture.whenStable();
    fixture.detectChanges();
    expect(q('execute-error')?.textContent).toContain('Falla');
    click('retry-execute');
    expect(api.execute).toHaveBeenCalledTimes(2);
    const first = api.execute.calls.argsFor(0);
    const second = api.execute.calls.argsFor(1);
    expect(first[2]).toBe(second[2]);
    expect(first[2].length).toBeGreaterThan(10);
  });

  it('shows import_running as a warning without losing the mapping', async () => {
    const { api, q, toPreviewStep, click, fixture, component } = create();
    api.execute.and.returnValue(throwError(() => new ImportApiError('Otra importación en curso', 409, 'import_running')));
    toPreviewStep();
    click('execute');
    await fixture.whenStable();
    fixture.detectChanges();
    expect(q('import-running')?.textContent).toContain('Otra importación en curso');
    expect(component.step).toBe(3);
    expect(component.mapping.controls.sale_date.value).toBe('Fecha');
  });

  it('shows the posting issues alert on 409 posting_configuration_missing', async () => {
    const { api, q, toPreviewStep, click, fixture } = create();
    api.execute.and.returnValue(
      throwError(() => new ImportApiError('Falta configuración', 409, 'posting_configuration_missing', {}, [
        { code: 'a', subject: 's', message: 'Falta la cuenta de ingresos' },
      ])),
    );
    toPreviewStep();
    click('execute');
    await fixture.whenStable();
    fixture.detectChanges();
    expect(q('config-missing')).not.toBeNull();
    expect(q('alert-posting-issues')?.textContent).toContain('Falta la cuenta de ingresos');
  });

  it('shows a warning result when some rows failed and restarts from «Corregir y subir de nuevo»', async () => {
    const { q, toPreviewStep, click, fixture, component } = create({
      execute: of({ id: 'run-1', status: 'COMPLETED', counts: { ...COUNTS, failed: 1 } }),
    });
    toPreviewStep();
    click('execute');
    await fixture.whenStable();
    fixture.detectChanges();
    expect(q('result-alert')?.classList.contains('alert-warning')).toBeTrue();
    click('fix-and-retry');
    expect(component.step).toBe(1);
    expect(component.upload).toBeNull();
  });
});
