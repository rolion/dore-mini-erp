import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { CrmApiError } from '../../models/board';
import { CrmBoardsApiService } from '../../services/crm-boards-api.service';
import { CrmInboxApiService } from '../../services/crm-inbox-api.service';
import { makeBoard, makeInboxConversation, makeOpportunity } from '../../testing/crm-fixtures';
import { InboxOpportunityDialogComponent } from './inbox-opportunity-dialog.component';

describe('InboxOpportunityDialogComponent', () => {
  let fixture: ComponentFixture<InboxOpportunityDialogComponent>;
  let component: InboxOpportunityDialogComponent;
  let api: jasmine.SpyObj<CrmInboxApiService>;
  let modal: jasmine.SpyObj<NgbActiveModal>;
  const withContact = makeInboxConversation({ contact: { type: 'customer', id: 'c-1', name: 'Ana' } });

  function setup(conversation = withContact, opportunities = [makeOpportunity()]): void {
    api = jasmine.createSpyObj<CrmInboxApiService>('CrmInboxApiService', ['linkableOpportunities', 'setOpportunity', 'createOpportunity']);
    api.linkableOpportunities.and.returnValue(of(opportunities));
    const boards = jasmine.createSpyObj<CrmBoardsApiService>('CrmBoardsApiService', ['list']);
    boards.list.and.returnValue(of([makeBoard()]));
    modal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    TestBed.configureTestingModule({
      imports: [InboxOpportunityDialogComponent],
      providers: [...provideTestTranslations(), { provide: CrmInboxApiService, useValue: api },
        { provide: CrmBoardsApiService, useValue: boards }, { provide: NgbActiveModal, useValue: modal }],
    });
    fixture = TestBed.createComponent(InboxOpportunityDialogComponent);
    component = fixture.componentInstance;
    component.open(conversation);
    fixture.detectChanges();
  }

  const q = (id: string): HTMLElement | null => (fixture.nativeElement as HTMLElement).querySelector(`[data-testid="${id}"]`);

  it('asks to link a contact first when the conversation has none (AC-07)', () => {
    setup(makeInboxConversation());
    expect(q('needs-contact')).not.toBeNull();
    expect(api.linkableOpportunities).not.toHaveBeenCalled();
    expect(component.canSubmit).toBeFalse();
  });

  it('links the chosen open opportunity', () => {
    setup();
    const updated = makeInboxConversation({ opportunity: { id: 'o-1', title: 'Combo familiar' } });
    api.setOpportunity.and.returnValue(of(updated));
    component.save();
    expect(api.setOpportunity).toHaveBeenCalledWith('v-1', 'o-1');
    expect(modal.close).toHaveBeenCalledWith(updated);
  });

  it('starts in create mode when the contact has no open opportunities', () => {
    setup(withContact, []);
    expect(component.mode).toBe('create');
    component.form.patchValue({ title: 'Desde chat', amount: '55.00' });
    api.createOpportunity.and.returnValue(of(makeInboxConversation()));
    component.save();
    expect(api.createOpportunity).toHaveBeenCalledWith('v-1', { boardId: 'b-1', title: 'Desde chat', amount: '55.00' });
  });

  it('does not create with a blank title or an invalid amount', () => {
    setup(withContact, []);
    component.form.patchValue({ title: '  ', amount: '55.00' });
    expect(component.canSubmit).toBeFalse();
    component.form.patchValue({ title: 'Ok', amount: 'abc' });
    expect(component.canSubmit).toBeFalse();
  });

  it('unlinks and shows server errors', () => {
    setup(makeInboxConversation({ contact: withContact.contact, opportunity: { id: 'o-1', title: 'Combo' } }));
    api.setOpportunity.and.returnValue(throwError(() => new CrmApiError('La oportunidad es de otro contacto.', 409, {}, 'contact_mismatch')));
    component.unlink();
    fixture.detectChanges();
    expect(api.setOpportunity).toHaveBeenCalledWith('v-1', null);
    expect(q('opportunity-error')?.textContent).toContain('otro contacto');
  });
});
