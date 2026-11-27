import { TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { CrmApiError } from '../../models/board';
import { CrmBoardsApiService } from '../../services/crm-boards-api.service';
import { makeBoard, makeStage } from '../../testing/crm-fixtures';
import { StageNameDialogComponent } from './stage-name-dialog.component';

describe('StageNameDialogComponent', () => {
  function setup() {
    const api = jasmine.createSpyObj<CrmBoardsApiService>('CrmBoardsApiService', ['addStage']);
    const modal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    TestBed.configureTestingModule({
      imports: [StageNameDialogComponent],
      providers: [...provideTestTranslations(), { provide: CrmBoardsApiService, useValue: api },
        { provide: NgbActiveModal, useValue: modal }],
    });
    const fixture = TestBed.createComponent(StageNameDialogComponent);
    fixture.componentInstance.boardId = 'b-1';
    fixture.detectChanges();
    return { fixture, component: fixture.componentInstance, api, modal };
  }

  it('requires a name and does not call the API when blank (AC-03)', () => {
    const { fixture, component, api } = setup();
    component.form.setValue({ name: '   ' });
    component.onSubmit();
    fixture.detectChanges();
    expect(api.addStage).not.toHaveBeenCalled();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Ingresa el nombre de la columna');
  });

  it('adds the column and closes with the updated board (AC-03)', () => {
    const { component, api, modal } = setup();
    const board = makeBoard({ stages: [makeStage({ name: 'Nuevo' })] });
    api.addStage.and.returnValue(of(board));
    component.form.setValue({ name: ' Nuevo ' });
    component.onSubmit();
    expect(api.addStage).toHaveBeenCalledOnceWith('b-1', 'Nuevo');
    expect(modal.close).toHaveBeenCalledOnceWith(board);
  });

  it('shows the server error for a duplicated name and stays open', () => {
    const { fixture, component, api, modal } = setup();
    api.addStage.and.returnValue(throwError(() => new CrmApiError('x', 400, { name: 'Ya existe una columna con ese nombre.' })));
    component.form.setValue({ name: 'Nuevo' });
    component.onSubmit();
    fixture.detectChanges();
    expect(modal.close).not.toHaveBeenCalled();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Ya existe una columna');
  });
});
