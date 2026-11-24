import { provideTestTranslations } from '../../../../core/i18n/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { of, throwError } from 'rxjs';
import { CrmApiError } from '../../models/board';
import { CrmBoardsApiService } from '../../services/crm-boards-api.service';
import { makeBoard, makeStage } from '../../testing/crm-fixtures';
import { ArchiveStageDialogComponent } from './archive-stage-dialog.component';

describe('ArchiveStageDialogComponent', () => {
  let fixture: ComponentFixture<ArchiveStageDialogComponent>;
  let component: ArchiveStageDialogComponent;
  let api: jasmine.SpyObj<CrmBoardsApiService>;
  let modal: jasmine.SpyObj<NgbActiveModal>;
  const a = makeStage({ id: 'a', name: 'A', cardCount: 0 });
  const b = makeStage({ id: 'b', name: 'B', position: 2 });
  const board = makeBoard({ stages: [a, b] });

  beforeEach(() => {
    api = jasmine.createSpyObj<CrmBoardsApiService>('CrmBoardsApiService', ['archiveStage']);
    modal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    TestBed.configureTestingModule({
      imports: [ArchiveStageDialogComponent],
      providers: [...provideTestTranslations(), { provide: CrmBoardsApiService, useValue: api },
        { provide: NgbActiveModal, useValue: modal }],
    });
    fixture = TestBed.createComponent(ArchiveStageDialogComponent);
    component = fixture.componentInstance;
  });

  const el = () => fixture.nativeElement as HTMLElement;
  const confirmButton = () => el().querySelector('.btn-warning') as HTMLButtonElement;

  it('archives directly when the stage has no cards', () => {
    api.archiveStage.and.returnValue(of(board));
    component.open(board, a);
    fixture.detectChanges();
    expect(el().querySelector('select')).toBeNull();
    confirmButton().click();
    expect(api.archiveStage).toHaveBeenCalledOnceWith('b-1', 'a', undefined);
    expect(modal.close).toHaveBeenCalledWith(board);
  });

  it('requires a destination when the stage has cards and sends it', () => {
    api.archiveStage.and.returnValue(of(board));
    component.open(board, makeStage({ id: 'a', name: 'A', cardCount: 4 }));
    fixture.detectChanges();
    expect(el().textContent).toContain('4 tarjetas');
    expect(Array.from(el().querySelectorAll('option')).map((o) => o.textContent?.trim())).toEqual(['Elige una etapa', 'B']);
    expect(confirmButton().disabled).toBeTrue();
    component.form.setValue({ target: 'b' });
    fixture.detectChanges();
    expect(confirmButton().disabled).toBeFalse();
    confirmButton().click();
    expect(api.archiveStage).toHaveBeenCalledOnceWith('b-1', 'a', 'b');
  });

  it('asks for a destination when the server reports cards the screen did not know about', () => {
    api.archiveStage.and.returnValue(throwError(() => new CrmApiError('Tiene tarjetas.', 409, {}, 'stage_has_cards', 2)));
    component.open(board, a);
    fixture.detectChanges();
    confirmButton().click();
    fixture.detectChanges();
    expect(modal.close).not.toHaveBeenCalled();
    expect(component.needsTarget).toBeTrue();
    expect(el().querySelector('select')).not.toBeNull();
    expect(el().textContent).toContain('Tiene tarjetas.');
  });
});
