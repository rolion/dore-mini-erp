import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { CrmApiError } from '../../models/board';
import { CrmBoardsApiService } from '../../services/crm-boards-api.service';
import { makeBoard } from '../../testing/crm-fixtures';
import { CrmTrackingBoardListComponent } from './crm-tracking-board-list.component';

describe('CrmTrackingBoardListComponent', () => {
  function setup(boards = [makeBoard({ id: 'b-1', name: 'Ventas' }), makeBoard({ id: 'b-2', name: 'Postventa' })]) {
    const api = jasmine.createSpyObj<CrmBoardsApiService>('CrmBoardsApiService', ['list']);
    api.list.and.returnValue(of(boards));
    const modal = jasmine.createSpyObj<NgbModal>('NgbModal', ['open']);
    TestBed.configureTestingModule({
      imports: [CrmTrackingBoardListComponent],
      providers: [...provideTestTranslations(), provideRouter([]),
        { provide: CrmBoardsApiService, useValue: api }, { provide: NgbModal, useValue: modal }],
    });
    const fixture = TestBed.createComponent(CrmTrackingBoardListComponent);
    fixture.detectChanges();
    return { fixture, api, modal, el: fixture.nativeElement as HTMLElement };
  }

  it('shows one tile per active board linking to its board (AC-01)', () => {
    const { api, el } = setup();
    expect(api.list).toHaveBeenCalledWith(true);
    const tiles = Array.from(el.querySelectorAll<HTMLAnchorElement>('[data-testid="board-tile"]'));
    expect(tiles.map((t) => t.textContent?.trim())).toEqual(['Ventas', 'Postventa']);
    expect(tiles[1].getAttribute('href')).toBe('/pocketbiz/crm/tracking/b-2');
  });

  it('shows the empty state and the create button when there are no boards', () => {
    const { el } = setup([]);
    expect(el.querySelector('[data-testid="no-boards"]')).toBeTruthy();
    expect(el.querySelector('[data-testid="create-board"]')?.textContent).toContain('Crear nuevo tablero');
  });

  it('shows an error with retry when loading fails', () => {
    const { fixture, api, el } = setup();
    api.list.and.returnValue(throwError(() => new CrmApiError('Sin conexión', 0)));
    fixture.componentInstance.load();
    fixture.detectChanges();
    expect(el.querySelector('[data-testid="load-error"]')?.textContent).toContain('Sin conexión');
  });

  it('opens the new board after creating it from the modal (AC-02)', async () => {
    const { fixture, modal } = setup();
    const router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    modal.open.and.returnValue({ result: Promise.resolve(makeBoard({ id: 'b-9', name: 'Nuevo' })) } as ReturnType<NgbModal['open']>);
    fixture.componentInstance.create();
    await fixture.whenStable();
    expect(router.navigate).toHaveBeenCalledWith(['/pocketbiz/crm/tracking', 'b-9']);
  });
});
