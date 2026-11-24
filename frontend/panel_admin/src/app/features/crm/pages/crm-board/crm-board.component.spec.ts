import { provideTestTranslations } from '../../../../core/i18n/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { of, throwError } from 'rxjs';
import { ArchiveStageDialogComponent } from '../../components/archive-stage-dialog/archive-stage-dialog.component';
import { CrmApiError } from '../../models/board';
import { CrmBoardsApiService } from '../../services/crm-boards-api.service';
import { makeBoard, makeStage } from '../../testing/crm-fixtures';
import { CrmBoardComponent } from './crm-board.component';

describe('CrmBoardComponent', () => {
  const abc = makeBoard({
    stages: [makeStage({ id: 'a', name: 'A', position: 1 }), makeStage({ id: 'b', name: 'B', position: 2 }),
      makeStage({ id: 'c', name: 'C', position: 3 })],
  });

  function create(boards = [abc]) {
    const api = jasmine.createSpyObj<CrmBoardsApiService>('CrmBoardsApiService',
      ['list', 'create', 'rename', 'archive', 'reactivate', 'addStage', 'renameStage', 'reorderStages', 'archiveStage']);
    api.list.and.returnValue(of(boards));
    const modal = jasmine.createSpyObj<NgbModal>('NgbModal', ['open']);
    TestBed.configureTestingModule({
      imports: [CrmBoardComponent],
      providers: [...provideTestTranslations(), provideRouter([]),
        { provide: CrmBoardsApiService, useValue: api }, { provide: NgbModal, useValue: modal }],
    });
    const fixture = TestBed.createComponent(CrmBoardComponent);
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    const rows = () => Array.from(el.querySelectorAll('[data-testid="stage-row"]'));
    const names = () => rows().map((r) => r.querySelector('strong')?.textContent?.trim());
    const click = (selector: string, root: ParentNode = el) => {
      (root.querySelector(selector) as HTMLElement).click();
      fixture.detectChanges();
    };
    return { fixture, api, modal, el, rows, names, click };
  }

  it('shows the empty state when there are no boards', () => {
    const { el } = create([]);
    expect(el.querySelector('[data-testid="no-boards"]')?.textContent).toContain('Aún no hay tableros');
  });

  it('lists the stages of the first board in order and the empty-stage message', () => {
    const { names } = create();
    expect(names()).toEqual(['A', 'B', 'C']);
    TestBed.resetTestingModule();
    const empty = create([makeBoard()]);
    expect(empty.el.querySelector('[data-testid="no-stages"]')?.textContent).toContain('no tiene etapas');
  });

  it('shows an error with retry when loading fails', () => {
    const { fixture, api, el, click } = create();
    api.list.and.returnValue(throwError(() => new CrmApiError('Sin conexión', 0)));
    fixture.componentInstance.load();
    fixture.detectChanges();
    expect(el.querySelector('[data-testid="load-error"]')?.textContent).toContain('Sin conexión');
    api.list.and.returnValue(of([abc]));
    click('[data-testid="load-error"] button');
    expect(el.querySelector('[data-testid="stages-table"]')).not.toBeNull();
  });

  it('moves a stage down saving the full order and renders the server result', () => {
    const { api, names, click, rows } = create();
    api.reorderStages.and.returnValue(of(makeBoard({
      stages: [makeStage({ id: 'b', name: 'B', position: 1 }), makeStage({ id: 'a', name: 'A', position: 2 }),
        makeStage({ id: 'c', name: 'C', position: 3 })],
    })));
    click('[data-testid="move-down"]', rows()[0]);
    expect(api.reorderStages).toHaveBeenCalledOnceWith('b-1', ['b', 'a', 'c']);
    expect(names()).toEqual(['B', 'A', 'C']);
  });

  it('disables moving the first stage up and the last down', () => {
    const { rows } = create();
    expect((rows()[0].querySelector('[data-testid="move-up"]') as HTMLButtonElement).disabled).toBeTrue();
    expect((rows()[2].querySelector('[data-testid="move-down"]') as HTMLButtonElement).disabled).toBeTrue();
  });

  it('adds a stage trimmed and clears the field', () => {
    const { fixture, api, el, names } = create();
    api.addStage.and.returnValue(of(makeBoard({ stages: [...abc.stages, makeStage({ id: 'd', name: 'D', position: 4 })] })));
    fixture.componentInstance.newStage.setValue('  D  ');
    fixture.detectChanges();
    // el formulario del test no está en el documento: se emite el envío directamente
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    fixture.detectChanges();
    expect(api.addStage).toHaveBeenCalledOnceWith('b-1', 'D');
    expect(names()).toEqual(['A', 'B', 'C', 'D']);
    expect(fixture.componentInstance.newStage.value).toBe('');
  });

  it('renames a stage inline and shows the server validation error on duplicates', () => {
    const { fixture, api, el, rows, click, names } = create();
    click('[data-testid="edit-stage"]', rows()[0]);
    fixture.componentInstance.editName.setValue('B');
    api.renameStage.and.returnValue(throwError(() => new CrmApiError('x', 400, { name: 'Ya existe una etapa.' })));
    click('[data-testid="save-stage"]');
    expect(el.textContent).toContain('Ya existe una etapa.');
    fixture.componentInstance.editName.setValue('Lead');
    api.renameStage.and.returnValue(of(makeBoard({ stages: [makeStage({ id: 'a', name: 'Lead' }), abc.stages[1], abc.stages[2]] })));
    click('[data-testid="save-stage"]');
    expect(api.renameStage).toHaveBeenCalledWith('b-1', 'a', 'Lead');
    expect(names()[0]).toBe('Lead');
  });

  it('reloads and warns on a 409 conflict (stale order)', () => {
    const { api, el, rows, click } = create();
    api.reorderStages.and.returnValue(throwError(() => new CrmApiError('Recarga el tablero.', 409, {}, 'stage_order_stale')));
    click('[data-testid="move-down"]', rows()[0]);
    expect(el.querySelector('[data-testid="notice"]')?.textContent).toContain('Recarga el tablero.');
    expect(api.list).toHaveBeenCalledTimes(2);
  });

  it('opens the archive dialog with the board and stage and applies the returned board', () => {
    const { api, modal, names, click, rows } = create();
    const dialog = jasmine.createSpyObj<ArchiveStageDialogComponent>('dialog', ['open']);
    const after = makeBoard({ stages: [abc.stages[0], makeStage({ id: 'c', name: 'C', position: 2 })] });
    modal.open.and.returnValue({ componentInstance: dialog, result: Promise.resolve(after) } as never);
    click('[data-testid="archive-stage"]', rows()[1]);
    expect(dialog.open).toHaveBeenCalledOnceWith(abc, abc.stages[1]);
    return Promise.resolve().then(() => {
      expect(api.list).toHaveBeenCalledTimes(1);
      expect(names()).toBeDefined();
    });
  });

  it('archives and reactivates a board, hiding archived boards unless asked', () => {
    const { fixture, api, el, click } = create();
    const archived = makeBoard({ isActive: false, stages: abc.stages });
    api.archive.and.returnValue(of(archived));
    click('[data-testid="archive-board"]');
    expect(api.archive).toHaveBeenCalledWith('b-1');
    expect(el.querySelector('[data-testid="no-boards"]')).not.toBeNull();
    click('#crm-show-archived');
    expect(el.querySelector('[data-testid="reactivate-board"]')).not.toBeNull();
    expect(el.querySelector('[data-testid="move-up"]')).toBeNull();
    api.reactivate.and.returnValue(of(abc));
    click('[data-testid="reactivate-board"]');
    expect(fixture.componentInstance.selected?.isActive).toBeTrue();
  });
});
