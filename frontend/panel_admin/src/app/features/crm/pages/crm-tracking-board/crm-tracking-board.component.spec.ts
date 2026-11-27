import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { CrmApiError } from '../../models/board';
import { CrmBoardsApiService } from '../../services/crm-boards-api.service';
import { CrmOpportunitiesApiService } from '../../services/crm-opportunities-api.service';
import { makeBoard, makeOpportunity, makeStage } from '../../testing/crm-fixtures';
import { CrmTrackingBoardComponent } from './crm-tracking-board.component';

describe('CrmTrackingBoardComponent', () => {
  const board = makeBoard({
    id: 'b-1', name: 'Clientes VIP',
    stages: [makeStage({ id: 's-2', name: 'Segunda', position: 2 }), makeStage({ id: 's-1', name: 'Primera', position: 1 })],
  });

  function setup(boards = [board], cards = [makeOpportunity({ id: 'o-1', stageId: 's-1', title: 'Llamar a Carla' })]) {
    const boardsApi = jasmine.createSpyObj<CrmBoardsApiService>('CrmBoardsApiService', ['list', 'archiveStage']);
    boardsApi.list.and.returnValue(of(boards));
    const opportunities = jasmine.createSpyObj<CrmOpportunitiesApiService>('CrmOpportunitiesApiService', ['list', 'move']);
    opportunities.list.and.returnValue(of({ count: cards.length, results: cards }));
    const modal = jasmine.createSpyObj<NgbModal>('NgbModal', ['open']);
    TestBed.configureTestingModule({
      imports: [CrmTrackingBoardComponent],
      providers: [...provideTestTranslations(), provideRouter([]),
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ boardId: 'b-1' }) } } },
        { provide: CrmBoardsApiService, useValue: boardsApi },
        { provide: CrmOpportunitiesApiService, useValue: opportunities }, { provide: NgbModal, useValue: modal }],
    });
    const fixture = TestBed.createComponent(CrmTrackingBoardComponent);
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    const names = () => Array.from(el.querySelectorAll('[data-testid="column-name"]')).map((n) => n.textContent?.trim());
    return { fixture, boardsApi, opportunities, modal, el, names };
  }

  it('shows the board name and its columns in position order with their cards by name (AC-03, AC-04)', () => {
    const { el, names } = setup();
    expect(el.querySelector('[data-testid="board-title"]')?.textContent).toContain('Clientes VIP');
    expect(names()).toEqual(['Primera', 'Segunda']);
    const columns = el.querySelectorAll('[data-testid="column"]');
    expect(columns[0].querySelector('[data-testid="tracking-card"]')?.textContent).toContain('Llamar a Carla');
    expect(columns[1].querySelector('[data-testid="column-empty"]')?.textContent).toContain('Sin tarjetas');
  });

  it('renders columns and cards in the Opportunities format: total, contact, amount, owner, add button (DDR v2)', () => {
    const { el } = setup();
    const column = el.querySelector('[data-testid="column"]') as HTMLElement;
    expect(column.querySelector('h5')?.textContent).toContain('Primera');
    expect(column.querySelector('h5')?.textContent).toContain('· 1');
    expect(column.querySelector('[data-testid="drag-handle"]')).toBeTruthy();
    expect(column.querySelector('[data-testid="card-contact"]')?.textContent).toContain('Carla Rojas');
    expect(column.querySelector('[data-testid="card-amount"]')?.textContent).toContain('150');
    expect(column.querySelector('[data-testid="add-card-button"]')?.textContent).toContain('Agregar');
  });

  it('moves a card to another column by dragging and reloads (DDR v2)', () => {
    const { fixture, opportunities } = setup();
    opportunities.move.and.returnValue(of(makeOpportunity()));
    const [first, second] = fixture.componentInstance.columns;
    fixture.componentInstance.drop({
      previousContainer: { data: first }, container: { data: second }, item: { data: first.cards[0] },
      previousIndex: 0, currentIndex: 0,
    } as never);
    expect(opportunities.move).toHaveBeenCalledOnceWith('o-1', 's-2');
    expect(opportunities.list).toHaveBeenCalledTimes(2);
  });

  it('opens an empty board with only the add-column action (AC-02)', () => {
    const { el } = setup([makeBoard({ id: 'b-1', name: 'Nuevo' })], []);
    expect(el.querySelector('[data-testid="no-columns"]')).toBeTruthy();
    expect(el.querySelector('[data-testid="add-column"]')).toBeTruthy();
  });

  it('shows not found when the board is not active or not from the company', () => {
    const { el } = setup([]);
    expect(el.querySelector('[data-testid="not-found"]')).toBeTruthy();
  });

  it('blocks archiving a column with active cards and tells to move them first (AC-05)', () => {
    const { fixture, boardsApi, el } = setup();
    fixture.componentInstance.requestArchive(fixture.componentInstance.columns[0]);
    fixture.detectChanges();
    expect(boardsApi.archiveStage).not.toHaveBeenCalled();
    expect(el.querySelector('[data-testid="notice"]')?.textContent).toContain('Muévelas');
    expect(el.querySelector('[data-testid="archive-confirm"]')).toBeNull();
  });

  it('archives an empty column after confirming and reloads (AC-05)', () => {
    const { fixture, boardsApi, el } = setup();
    boardsApi.archiveStage.and.returnValue(of(board));
    fixture.componentInstance.requestArchive(fixture.componentInstance.columns[1]);
    fixture.detectChanges();
    (el.querySelector('[data-testid="archive-yes"]') as HTMLElement).click();
    expect(boardsApi.archiveStage).toHaveBeenCalledOnceWith('b-1', 's-2');
    expect(boardsApi.list).toHaveBeenCalledTimes(2);
  });

  it('warns and reloads when the server blocks the archive with 409 (AC-05)', () => {
    const { fixture, boardsApi, el } = setup();
    boardsApi.archiveStage.and.returnValue(throwError(() => new CrmApiError('x', 409, {}, 'stage_has_cards', 2)));
    fixture.componentInstance.requestArchive(fixture.componentInstance.columns[1]);
    fixture.componentInstance.confirmArchive();
    fixture.detectChanges();
    expect(el.querySelector('[data-testid="notice"]')?.textContent).toContain('2 tarjeta');
    expect(boardsApi.list).toHaveBeenCalledTimes(2);
  });

  it('opens the card dialog for the column it was launched from and reloads after saving (AC-06)', async () => {
    const { fixture, modal, opportunities } = setup();
    const dialog = jasmine.createSpyObj('TrackingCardDialogComponent', ['open']);
    modal.open.and.returnValue({ componentInstance: dialog, result: Promise.resolve(makeOpportunity()) } as unknown as ReturnType<NgbModal['open']>);
    fixture.componentInstance.addCard(fixture.componentInstance.columns[1]);
    await fixture.whenStable();
    expect(dialog.open).toHaveBeenCalledWith({ boardId: 'b-1', stageId: 's-2' });
    expect(opportunities.list).toHaveBeenCalledTimes(2);
  });
});
