import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NgbActiveModal, NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { CrmApiError } from '../../models/board';
import { CrmCustomersApiService } from '../../services/crm-customers-api.service';
import { CrmInboxApiService } from '../../services/crm-inbox-api.service';
import { CrmLeadsApiService } from '../../services/crm-leads-api.service';
import { LeadDialogComponent } from '../lead-dialog/lead-dialog.component';
import { makeInboxConversation, makeLead } from '../../testing/crm-fixtures';
import { InboxContactDialogComponent } from './inbox-contact-dialog.component';

describe('InboxContactDialogComponent', () => {
  let fixture: ComponentFixture<InboxContactDialogComponent>;
  let component: InboxContactDialogComponent;
  let api: jasmine.SpyObj<CrmInboxApiService>;
  let modal: jasmine.SpyObj<NgbActiveModal>;
  let ngb: jasmine.SpyObj<NgbModal>;

  function setup(contact = makeInboxConversation().contact): void {
    api = jasmine.createSpyObj<CrmInboxApiService>('CrmInboxApiService', ['setContact']);
    modal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    ngb = jasmine.createSpyObj<NgbModal>('NgbModal', ['open']);
    TestBed.configureTestingModule({
      imports: [InboxContactDialogComponent],
      providers: [...provideTestTranslations(), { provide: CrmInboxApiService, useValue: api }, { provide: NgbActiveModal, useValue: modal }, { provide: NgbModal, useValue: ngb },
        { provide: CrmLeadsApiService, useValue: jasmine.createSpyObj('CrmLeadsApiService', ['list']) },
        { provide: CrmCustomersApiService, useValue: jasmine.createSpyObj('CrmCustomersApiService', ['list']) }],
    });
    fixture = TestBed.createComponent(InboxContactDialogComponent);
    component = fixture.componentInstance;
    component.open(makeInboxConversation({ contact }));
    fixture.detectChanges();
  }

  it('links the chosen customer and closes with the updated conversation (AC-06)', () => {
    setup();
    const updated = makeInboxConversation({ contact: { type: 'customer', id: 'c-1', name: 'Ana' } });
    api.setContact.and.returnValue(of(updated));
    component.form.controls.contact.setValue({ id: 'c-1', name: 'Ana', phone: '+591' });
    component.save();
    expect(api.setContact).toHaveBeenCalledWith('v-1', { type: 'customer', id: 'c-1' });
    expect(modal.close).toHaveBeenCalledWith(updated);
  });

  it('does not save without a contact', () => {
    setup();
    component.save();
    expect(api.setContact).not.toHaveBeenCalled();
  });

  it('removes the contact only when there is one', () => {
    setup({ type: 'lead', id: 'l-1', name: 'Lia' });
    expect((fixture.nativeElement as HTMLElement).querySelector('[data-testid="remove-contact"]')).not.toBeNull();
    api.setContact.and.returnValue(of(makeInboxConversation()));
    component.remove();
    expect(api.setContact).toHaveBeenCalledWith('v-1', null);
  });

  it('creates a lead with the conversation phone and links it (UI-04)', async () => {
    setup();
    const lead = makeLead({ id: 'l-9' });
    const form = { patchValue: jasmine.createSpy('patchValue') };
    ngb.open.and.returnValue({ componentInstance: { form }, result: Promise.resolve(lead) } as never);
    api.setContact.and.returnValue(of(makeInboxConversation()));
    component.form.controls.kind.setValue('lead');
    fixture.detectChanges();
    (fixture.nativeElement as HTMLElement).querySelector<HTMLButtonElement>('[data-testid="create-lead"]')?.click();
    await Promise.resolve();
    expect(ngb.open).toHaveBeenCalledWith(LeadDialogComponent, jasmine.anything());
    expect(form.patchValue).toHaveBeenCalledWith({ phone: '+59176543210' });
    expect(api.setContact).toHaveBeenCalledWith('v-1', { type: 'lead', id: 'l-9' });
  });

  it('shows the server error and stays open', () => {
    setup();
    api.setContact.and.returnValue(throwError(() => new CrmApiError('El cliente está inactivo.', 409, {}, 'customer_inactive')));
    component.form.controls.contact.setValue({ id: 'c-1', name: 'Ana', phone: '' });
    component.save();
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).querySelector('[data-testid="contact-error"]')?.textContent).toContain('inactivo');
    expect(modal.close).not.toHaveBeenCalled();
  });
});
