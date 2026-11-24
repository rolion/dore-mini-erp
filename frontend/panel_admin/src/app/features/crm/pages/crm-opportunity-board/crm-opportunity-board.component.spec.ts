import { provideTestTranslations } from '../../../../core/i18n/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { fakeAsync, tick } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { AuthService } from '../../../../core/service/auth.service';
import { ModulesService } from '../../../../core/service/modules.service';
import { CLOSE_DIALOG_CONVERT, CloseOpportunityDialogComponent } from '../../components/close-opportunity-dialog/close-opportunity-dialog.component';
import { ConvertLeadDialogComponent } from '../../components/convert-lead-dialog/convert-lead-dialog.component';
import { OpportunityDialogComponent } from '../../components/opportunity-dialog/opportunity-dialog.component';
import { CrmApiError, CrmBoard } from '../../models/board';
import { CrmOpportunity } from '../../models/opportunity';
import { CrmBoardsApiService } from '../../services/crm-boards-api.service';
import { CrmCustomersApiService } from '../../services/crm-customers-api.service';
import { CrmLeadsApiService } from '../../services/crm-leads-api.service';
import { CrmOpportunitiesApiService } from '../../services/crm-opportunities-api.service';
import { CrmUsersApiService } from '../../services/crm-users-api.service';
import { makeBoard, makeOpportunity, makeStage } from '../../testing/crm-fixtures';
import { CrmOpportunityBoardComponent } from './crm-opportunity-board.component';

describe('CrmOpportunityBoardComponent', () => {
  const board = makeBoard({
    stages: [makeStage({ id: 's-1', name: 'Nuevo' }), makeStage({ id: 's-2', name: 'Propuesta', position: 2 })],
  });
  const leadCard = makeOpportunity({ id: 'o-1', stageId: 's-1', amount: '100.00', nextActionAt: '2020-01-01T10:00:00Z' });
  const customerCard = makeOpportunity({
    id: 'o-2', stageId: 's-1', title: 'Pedido grande', amount: '50.50', lead: null,
    customer: { id: 'c-1', name: 'Beto Díaz', phone: '+59170000000' }, owner: { id: 9, name: 'Beto Vendedor' },
  });

  function create(boards: CrmBoard[] = [board], cards: CrmOpportunity[] = [leadCard, customerCard], salesEnabled = true) {
    const boardsApi = jasmine.createSpyObj<CrmBoardsApiService>('CrmBoardsApiService', ['list']);
    boardsApi.list.and.returnValue(of(boards));
    const api = jasmine.createSpyObj<CrmOpportunitiesApiService>('CrmOpportunitiesApiService', ['list', 'move']);
    api.list.and.returnValue(of({ count: cards.length, results: cards }));
    const usersApi = jasmine.createSpyObj<CrmUsersApiService>('CrmUsersApiService', ['list']);
    usersApi.list.and.returnValue(of([{ id: 7, name: 'Ana Admin' }, { id: 11, name: 'Carlos Compa' }]));
    const leadsApi = jasmine.createSpyObj<CrmLeadsApiService>('CrmLeadsApiService', ['list']);
    leadsApi.list.and.returnValue(of({ count: 0, results: [] }));
    const customersApi = jasmine.createSpyObj<CrmCustomersApiService>('CrmCustomersApiService', ['list']);
    customersApi.list.and.returnValue(of({ count: 0, results: [], meta: { sales_enabled: true, warehouse_filter_enabled: true } }));
    const modal = jasmine.createSpyObj<NgbModal>('NgbModal', ['open']);
    TestBed.configureTestingModule({
      imports: [CrmOpportunityBoardComponent],
      providers: [
        ...provideTestTranslations(), provideRouter([]),
        { provide: CrmBoardsApiService, useValue: boardsApi },
        { provide: CrmOpportunitiesApiService, useValue: api },
        { provide: CrmUsersApiService, useValue: usersApi },
        { provide: CrmLeadsApiService, useValue: leadsApi },
        { provide: CrmCustomersApiService, useValue: customersApi },
        { provide: NgbModal, useValue: modal },
        { provide: ModulesService, useValue: { enabledKeysValue: new Set(salesEnabled ? ['customers', 'sales'] : ['customers']) } },
        { provide: AuthService, useValue: { currentUserValue: { id: 7, username: 'ana', firstName: 'Ana', lastName: 'Admin' } } },
      ],
    });
    const fixture = TestBed.createComponent(CrmOpportunityBoardComponent);
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    const columns = (): HTMLElement[] => Array.from(el.querySelectorAll('[data-testid="column"]'));
    const cardsIn = (column: HTMLElement): HTMLElement[] => Array.from(column.querySelectorAll('[data-testid="opportunity-card"]'));
    return { fixture, component: fixture.componentInstance, boardsApi, api, usersApi, leadsApi, customersApi, modal, el, columns, cardsIn };
  }

  function dialog<T>(modal: jasmine.SpyObj<NgbModal>, instance: jasmine.SpyObj<T>, result: Promise<unknown>): void {
    modal.open.and.returnValue({ componentInstance: instance, result } as never);
  }

  it('renders one column per active stage with count, total and the cards of each stage (AC-10, UI-02)', () => {
    const { api, columns, cardsIn } = create();
    expect(api.list).toHaveBeenCalledWith({
      boardId: 'b-1', status: 'open', ownerId: undefined, leadId: undefined, customerId: undefined, pageSize: 200,
    });
    const [first, second] = columns();
    expect(first.querySelector('h5')?.textContent).toContain('Nuevo · 2');
    expect(first.textContent).toContain('Bs 150.50');
    expect(cardsIn(first).length).toBe(2);
    expect(second.querySelector('[data-testid="column-empty"]')?.textContent).toContain('Sin oportunidades');
  });

  it('shows contact, amount, overdue next action and owner on each card', () => {
    const { columns, cardsIn } = create();
    const [lead, customer] = cardsIn(columns()[0]);
    expect(lead.querySelector('[data-testid="card-contact"]')?.textContent).toContain('Carla Rojas');
    expect(lead.querySelector('[data-testid="card-contact"]')?.textContent).toContain('(Prospecto)');
    expect(lead.querySelector('[data-testid="card-amount"]')?.textContent).toContain('Bs 100.00');
    const next = lead.querySelector('[data-testid="card-next"]') as HTMLElement;
    expect(next.textContent).toContain('Vencida');
    expect(next.classList).toContain('text-danger');
    expect(customer.querySelector('[data-testid="card-contact"]')?.textContent).toContain('Beto Díaz · +59170000000');
    expect(customer.querySelector('[data-testid="convert-lead"]')).toBeNull();
    expect(customer.textContent).toContain('Beto Vendedor');
  });

  it('moves a card with «Mover a…» to another stage of the same board and reloads (UI-03)', () => {
    const { fixture, api, el, columns, cardsIn } = create();
    const select = cardsIn(columns()[0])[0].querySelector('[data-testid="move-select"]') as HTMLSelectElement;
    expect(Array.from(select.options).map((o) => o.textContent?.trim())).toEqual(['Mover a…', 'Propuesta']);
    expect(select.labels?.[0]?.textContent).toContain('Mover «Combo familiar» a…');
    api.move.and.returnValue(of(makeOpportunity({ stageId: 's-2' })));
    select.value = 's-2';
    select.dispatchEvent(new Event('change'));
    fixture.detectChanges();
    expect(api.move).toHaveBeenCalledOnceWith('o-1', 's-2');
    expect(api.list).toHaveBeenCalledTimes(2);
    expect(el.querySelector('[data-testid="success"]')?.textContent).toContain('se movió de etapa');
  });

  it('offers every company user as owner, not only those already on the board (REV-03)', () => {
    const { component, usersApi } = create();
    expect(usersApi.list).toHaveBeenCalledTimes(1);
    expect(component.ownerOptions.map((o) => o.id)).toContain(11); // Carlos no tiene tarjetas en el tablero
  });

  it('keeps the known owners when the users endpoint fails', () => {
    const { component, usersApi } = create();
    usersApi.list.and.returnValue(throwError(() => new CrmApiError('Error', 500, {})));
    expect(component.ownerOptions.map((o) => o.id)).toEqual([7, 9, 11]);
  });

  it('searches leads and customers by free text and adds them to the contact filter (REV-03)', fakeAsync(() => {
    const { component, leadsApi, customersApi } = create();
    leadsApi.list.and.returnValue(of({ count: 1, results: [{
      id: 'l-9', name: 'Dora Nueva', phone: '', normalizedPhone: '', email: '', convertedCustomerId: null, createdAt: '',
    }] }));
    customersApi.list.and.returnValue(of({ count: 1, results: [{
      id: 'c-9', name: 'Dora Cliente', phone: '', lastPurchaseAt: null, orderCount: 0, outstandingAmount: '0.00',
      currency: 'BOB',
    }], meta: { sales_enabled: true, warehouse_filter_enabled: true } }));
    component.contactSearch$.next('dora');
    tick(250);
    expect(leadsApi.list).toHaveBeenCalledWith({ search: 'dora', pageSize: 20 });
    expect(customersApi.list).toHaveBeenCalledWith({ search: 'dora', pageSize: 20 });
    const labels = component.contactOptions.map((o) => o.label);
    expect(labels).toContain('Dora Nueva (Prospecto)');
    expect(labels).toContain('Dora Cliente (Cliente)');
    expect(component.contactsLoading).toBeFalse();
  }));

  it('survives a failed contact search', fakeAsync(() => {
    const { component, leadsApi } = create();
    leadsApi.list.and.returnValue(throwError(() => new CrmApiError('Error', 500, {})));
    component.contactSearch$.next('x');
    tick(250);
    expect(component.contactsLoading).toBeFalse();
    expect(component.contactOptions.length).toBe(2);
  }));

  it('warns and reloads when moving fails with a 409', () => {
    const { fixture, component, api, el } = create();
    api.move.and.returnValue(throwError(() => new CrmApiError('La oportunidad ya está cerrada.', 409, {}, 'opportunity_closed')));
    component.move(leadCard, 's-2');
    fixture.detectChanges();
    expect(el.querySelector('[data-testid="notice"]')?.textContent).toContain('La oportunidad ya está cerrada.');
    expect(api.list).toHaveBeenCalledTimes(2);
  });

  it('filters by owner and by lead or customer on the server and offers to clear filters (AC-07, AC-10)', () => {
    const { fixture, component, api, el } = create();
    expect(component.ownerOptions.map((o) => o.name)).toEqual(['Ana Admin', 'Beto Vendedor', 'Carlos Compa']);
    expect(component.contactOptions.map((o) => o.key)).toEqual(['customer:c-1', 'lead:l-1']);
    api.list.and.returnValue(of({ count: 0, results: [] }));
    component.filters.controls.ownerId.setValue('9');
    expect(api.list).toHaveBeenCalledWith(jasmine.objectContaining({ ownerId: 9 }));
    component.filters.controls.contact.setValue('lead:l-1');
    expect(api.list).toHaveBeenCalledWith(jasmine.objectContaining({ ownerId: 9, leadId: 'l-1', customerId: undefined }));
    fixture.detectChanges();
    expect(el.querySelector('[data-testid="empty-filtered"]')?.textContent).toContain('No hay oportunidades que coincidan');
    expect(component.ownerOptions.length).toBe(3); // los filtros conservan las opciones ya vistas
    component.filters.controls.contact.setValue('customer:c-1');
    expect(api.list).toHaveBeenCalledWith(jasmine.objectContaining({ leadId: undefined, customerId: 'c-1' }));
    (el.querySelector('[data-testid="empty-filtered"] button') as HTMLButtonElement).click();
    expect(component.filters.getRawValue()).toEqual({ ownerId: '', contact: '', status: 'open' });
  });

  it('shows closed opportunities read-only with their badge (status filter)', () => {
    const won = makeOpportunity({ status: 'won', closedAt: '2026-11-22T10:00:00Z', customer: { id: 'c-1', name: 'Beto', phone: '' } });
    const { fixture, component, api, el } = create();
    api.list.and.returnValue(of({ count: 1, results: [won] }));
    component.filters.controls.status.setValue('won');
    fixture.detectChanges();
    expect(api.list).toHaveBeenCalledWith(jasmine.objectContaining({ status: 'won' }));
    expect(el.querySelector('[data-testid="badge-won"]')?.textContent).toContain('Ganada');
    expect(el.querySelector('[data-testid="move-select"]')).toBeNull();
    expect(el.querySelector('[data-testid="link-order"]')).not.toBeNull();
  });

  it('shows the empty states: no boards and board without stages, with a link to configure', () => {
    const empty = create([]);
    expect(empty.el.querySelector('[data-testid="no-boards"] a')?.getAttribute('href')).toContain('/pocketbiz/crm/board');
    expect(empty.api.list).not.toHaveBeenCalled();
    TestBed.resetTestingModule();
    const noStages = create([makeBoard()]);
    expect(noStages.el.querySelector('[data-testid="no-stages"]')?.textContent).toContain('no tiene etapas activas');
    expect(noStages.el.querySelector('[data-testid="new-opportunity"]')).toBeNull();
  });

  it('shows load errors with retry for boards and cards', () => {
    const { fixture, component, boardsApi, api, el } = create();
    api.list.and.returnValue(throwError(() => new CrmApiError('No se pudo conectar con el servidor.', 0)));
    component.reload();
    fixture.detectChanges();
    expect(el.querySelector('[data-testid="cards-error"]')?.textContent).toContain('No se pudo conectar');
    api.list.and.returnValue(of({ count: 0, results: [] }));
    (el.querySelector('[data-testid="cards-error"] button') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(el.querySelector('[data-testid="kanban"]')).not.toBeNull();
    boardsApi.list.and.returnValue(throwError(() => new CrmApiError('Error del servidor.', 500)));
    component.loadBoards();
    fixture.detectChanges();
    expect(el.querySelector('[data-testid="boards-error"]')?.textContent).toContain('Error del servidor.');
  });

  it('opens the opportunity dialog with the board, known owners and current user, then reloads', async () => {
    const { component, api, modal, el } = create();
    const instance = jasmine.createSpyObj<OpportunityDialogComponent>('dialog', ['open']);
    dialog(modal, instance, Promise.resolve(makeOpportunity()));
    (el.querySelector('[data-testid="new-opportunity"]') as HTMLButtonElement).click();
    expect(modal.open).toHaveBeenCalledWith(OpportunityDialogComponent, jasmine.any(Object));
    expect(instance.open).toHaveBeenCalledOnceWith(jasmine.objectContaining({
      board, currentUser: { id: 7, name: 'Ana Admin' }, stageId: undefined,
    }));
    await Promise.resolve();
    expect(api.list).toHaveBeenCalledTimes(2);
    expect(component.success).toBe('Oportunidad creada.');
  });

  it('opens the close dialog with the Sales flag and converts the lead when asked', async () => {
    const { component, modal } = create([board], [leadCard], false);
    const close = jasmine.createSpyObj<CloseOpportunityDialogComponent>('close', ['open']);
    const convert = jasmine.createSpyObj<ConvertLeadDialogComponent>('convert', ['open']);
    modal.open.and.returnValues(
      { componentInstance: close, result: Promise.reject(CLOSE_DIALOG_CONVERT) } as never,
      { componentInstance: convert, result: new Promise(() => undefined) } as never,
    );
    component.close(leadCard);
    expect(close.open).toHaveBeenCalledOnceWith(leadCard, false);
    await Promise.resolve();
    await Promise.resolve();
    expect(modal.open).toHaveBeenCalledWith(ConvertLeadDialogComponent, jasmine.any(Object));
    expect(convert.open).toHaveBeenCalledOnceWith(leadCard.lead!);
  });
});
