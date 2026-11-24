import { provideTestTranslations } from '../../../../core/i18n/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { of, throwError } from 'rxjs';
import { CrmApiError } from '../../models/board';
import { CrmBoardsApiService } from '../../services/crm-boards-api.service';
import { makeBoard } from '../../testing/crm-fixtures';
import { BoardNameDialogComponent } from './board-name-dialog.component';

describe('BoardNameDialogComponent', () => {
  let fixture: ComponentFixture<BoardNameDialogComponent>;
  let component: BoardNameDialogComponent;
  let api: jasmine.SpyObj<CrmBoardsApiService>;
  let modal: jasmine.SpyObj<NgbActiveModal>;

  beforeEach(() => {
    api = jasmine.createSpyObj<CrmBoardsApiService>('CrmBoardsApiService', ['create', 'rename']);
    modal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    TestBed.configureTestingModule({
      imports: [BoardNameDialogComponent],
      providers: [...provideTestTranslations(), { provide: CrmBoardsApiService, useValue: api },
        { provide: NgbActiveModal, useValue: modal }],
    });
    fixture = TestBed.createComponent(BoardNameDialogComponent);
    component = fixture.componentInstance;
  });

  const text = () => (fixture.nativeElement as HTMLElement).textContent ?? '';

  it('requires a name', () => {
    fixture.detectChanges();
    component.onSubmit();
    fixture.detectChanges();
    expect(api.create).not.toHaveBeenCalled();
    expect(text()).toContain('El nombre es obligatorio.');
  });

  it('creates a board with the trimmed name and closes with it', () => {
    const saved = makeBoard({ name: 'Ventas' });
    api.create.and.returnValue(of(saved));
    fixture.detectChanges();
    component.form.setValue({ name: ' Ventas ' });
    component.onSubmit();
    expect(api.create).toHaveBeenCalledOnceWith('Ventas');
    expect(modal.close).toHaveBeenCalledWith(saved);
  });

  it('renames an existing board and shows the duplicate-name error', () => {
    component.edit(makeBoard({ id: 'b-9', name: 'Ventas' }));
    fixture.detectChanges();
    expect(text()).toContain('Renombrar tablero');
    api.rename.and.returnValue(throwError(() => new CrmApiError('x', 400, { name: 'Ya existe un tablero.' })));
    component.form.setValue({ name: 'Otro' });
    component.onSubmit();
    fixture.detectChanges();
    expect(api.rename).toHaveBeenCalledWith('b-9', 'Otro');
    expect(text()).toContain('Ya existe un tablero.');
    expect(modal.close).not.toHaveBeenCalled();
  });
});
