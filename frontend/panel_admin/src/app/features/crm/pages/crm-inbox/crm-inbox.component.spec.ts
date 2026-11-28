import { ComponentFixture, TestBed, fakeAsync, flush, tick, discardPeriodicTasks } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { CrmApiError } from '../../models/board';
import { CrmInboxApiService } from '../../services/crm-inbox-api.service';
import { CrmUsersApiService } from '../../services/crm-users-api.service';
import { makeInboxConversation, makeInboxMessage } from '../../testing/crm-fixtures';
import { CrmInboxComponent, INBOX_POLL_MS } from './crm-inbox.component';

describe('CrmInboxComponent', () => {
  let fixture: ComponentFixture<CrmInboxComponent>;
  let component: CrmInboxComponent;
  let api: jasmine.SpyObj<CrmInboxApiService>;
  let modal: jasmine.SpyObj<NgbModal>;
  const open = makeInboxConversation({ id: 'v-1' });
  const closed = makeInboxConversation({ id: 'v-2', phone: '59171112222', windowOpen: false });

  function setup(rows = [open, closed]): void {
    api = jasmine.createSpyObj<CrmInboxApiService>('CrmInboxApiService', [
      'list', 'get', 'messages', 'sendText', 'sendTemplate', 'retry', 'assign', 'approvedTemplates']);
    api.list.and.returnValue(of({ count: rows.length, results: rows }));
    api.get.and.callFake((id: string) => of({ ...rows.find((r) => r.id === id)!, connectionActive: true }));
    api.messages.and.returnValue(of([makeInboxMessage()]));
    api.approvedTemplates.and.returnValue(of([{ id: 't-1', name: 'hola', language: 'es' }]));
    api.sendText.and.returnValue(of(makeInboxMessage({ id: 'm-2', direction: 'out', status: 'queued' })));
    api.sendTemplate.and.returnValue(of(makeInboxMessage({ id: 'm-3', direction: 'out', type: 'template', status: 'queued' })));
    modal = jasmine.createSpyObj<NgbModal>('NgbModal', ['open']);
    const users = jasmine.createSpyObj<CrmUsersApiService>('CrmUsersApiService', ['list']);
    users.list.and.returnValue(of([{ id: 7, name: 'Ana Admin' }]));
    TestBed.configureTestingModule({
      imports: [CrmInboxComponent],
      providers: [...provideTestTranslations(), provideRouter([]), { provide: CrmInboxApiService, useValue: api },
        { provide: CrmUsersApiService, useValue: users }, { provide: NgbModal, useValue: modal }],
    });
    fixture = TestBed.createComponent(CrmInboxComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  const root = (): HTMLElement => fixture.nativeElement as HTMLElement;
  const q = (id: string): HTMLElement | null => root().querySelector(`[data-testid="${id}"]`);

  it('lists the conversations and shows the closed-window badge (UI-02)', () => {
    setup();
    expect(root().querySelectorAll('[data-testid="conversation-row"]').length).toBe(2);
    expect(root().textContent).toContain('59171112222');
    expect(api.list).toHaveBeenCalledWith(jasmine.objectContaining({ scope: 'all', page: 1 }));
  });

  it('shows the empty state with a link to the WhatsApp settings', () => {
    setup([]);
    expect(q('empty')?.textContent).toContain('Aún no hay conversaciones');
    expect(q('empty')?.querySelector('a')?.getAttribute('href')).toContain('/settings/integrations/whatsapp');
  });

  it('shows an error with retry when the list fails', () => {
    setup();
    api.list.and.returnValue(throwError(() => new CrmApiError('Sin conexión', 0)));
    component.retry();
    fixture.detectChanges();
    expect(q('inbox-error')?.textContent).toContain('Sin conexión');
  });

  it('opens a conversation: loads the thread and offers the reply box (UI-03)', () => {
    setup();
    component.open(open);
    fixture.detectChanges();
    expect(api.messages).toHaveBeenCalledWith('v-1');
    expect(q('thread-title')?.textContent).toContain('59176543210');
    expect(root().querySelectorAll('[data-testid="message"]').length).toBe(1);
    expect(q('reply')).not.toBeNull();
    expect(q('window-closed')).toBeNull();
  });

  it('sends the typed text and reloads the thread', () => {
    setup();
    component.open(open);
    component.replyControl.setValue('  Hola Ana ');
    component.send();
    expect(api.sendText).toHaveBeenCalledWith('v-1', 'Hola Ana');
    expect(component.replyControl.value).toBe('');
    expect(api.messages).toHaveBeenCalledTimes(2);
  });

  it('with the window closed only a template can be sent (UI-03)', () => {
    setup();
    component.open(closed);
    fixture.detectChanges();
    expect(q('reply')).toBeNull();
    expect(q('window-closed')).not.toBeNull();
    component.templateControl.setValue('t-1');
    component.sendTemplate();
    expect(api.sendTemplate).toHaveBeenCalledWith('v-2', 't-1');
  });

  it('shows the 409 message when the server rejects the reply', () => {
    setup();
    api.sendText.and.returnValue(throwError(() => new CrmApiError('La ventana de 24 h está cerrada', 409, {}, 'window_closed')));
    component.open(open);
    component.replyControl.setValue('Hola');
    component.send();
    fixture.detectChanges();
    expect(q('action-error')?.textContent).toContain('24 h');
    expect(component.replyControl.value).toBe('Hola');
  });

  it('resends a failed message with its reason visible', () => {
    setup();
    api.messages.and.returnValue(of([makeInboxMessage({ id: 'm-9', direction: 'out', status: 'failed', failureReason: '400 inválido' })]));
    api.retry.and.returnValue(of(makeInboxMessage({ id: 'm-9', direction: 'out', status: 'queued' })));
    component.open(open);
    fixture.detectChanges();
    expect(q('failure')?.textContent).toContain('400 inválido');
    (q('resend') as HTMLButtonElement).click();
    expect(api.retry).toHaveBeenCalledWith('v-1', 'm-9');
  });

  it('assigns the owner and clears it', () => {
    setup();
    api.assign.and.returnValue(of({ ...open, owner: { id: 7, name: 'Ana Admin' } }));
    component.open(open);
    component.assign('7');
    expect(api.assign).toHaveBeenCalledWith('v-1', 7);
    expect(component.selected?.owner?.name).toBe('Ana Admin');
    component.assign('');
    expect(api.assign).toHaveBeenCalledWith('v-1', null);
  });

  it('refreshes the list when the scope changes and goes back to the list (UI-06)', () => {
    setup();
    component.scopeControl.setValue('mine');
    expect(api.list).toHaveBeenCalledWith(jasmine.objectContaining({ scope: 'mine', page: 1 }));
    component.open(open);
    component.back();
    expect(component.selected).toBeNull();
  });

  it('polls only while the tab is visible and stops on destroy (UI-05)', fakeAsync(() => {
    setup();
    component.open(open);
    const before = api.messages.calls.count();
    tick(INBOX_POLL_MS);
    expect(api.messages.calls.count()).toBe(before + 1);
    fixture.destroy();
    tick(INBOX_POLL_MS * 3);
    expect(api.messages.calls.count()).toBe(before + 1);
    discardPeriodicTasks();
    flush();
  }));
});
