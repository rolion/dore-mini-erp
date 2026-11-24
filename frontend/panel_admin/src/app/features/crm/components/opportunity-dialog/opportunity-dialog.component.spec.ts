import { provideTestTranslations } from '../../../../core/i18n/testing';
import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { of, throwError } from 'rxjs';
import { CrmApiError } from '../../models/board';
import { CrmCustomersApiService } from '../../services/crm-customers-api.service';
import { CrmLeadsApiService } from '../../services/crm-leads-api.service';
import { CrmOpportunitiesApiService } from '../../services/crm-opportunities-api.service';
import { makeBoard, makeCrmCustomer, makeCrmPage, makeLead, makeOpportunity, makeStage } from '../../testing/crm-fixtures';
import { OpportunityDialogComponent, OpportunityDialogContext, fromLocalInput, toLocalInput } from './opportunity-dialog.component';

describe('OpportunityDialogComponent', () => {
  let fixture: ComponentFixture<OpportunityDialogComponent>;
  let component: OpportunityDialogComponent;
  let api: jasmine.SpyObj<CrmOpportunitiesApiService>;
  let leads: jasmine.SpyObj<CrmLeadsApiService>;
  let customers: jasmine.SpyObj<CrmCustomersApiService>;
  let modal: jasmine.SpyObj<NgbActiveModal>;
  const board = makeBoard({ stages: [makeStage({ id: 's-1', name: 'Nuevo' }), makeStage({ id: 's-2', name: 'Propuesta', position: 2 })] });
  const me = { id: 7, name: 'Ana Admin' };

  function setup(context: Partial<OpportunityDialogContext> = {}): void {
    api = jasmine.createSpyObj<CrmOpportunitiesApiService>('CrmOpportunitiesApiService', ['create', 'update']);
    leads = jasmine.createSpyObj<CrmLeadsApiService>('CrmLeadsApiService', ['list']);
    leads.list.and.returnValue(of({ count: 1, results: [makeLead()] }));
    customers = jasmine.createSpyObj<CrmCustomersApiService>('CrmCustomersApiService', ['list']);
    customers.list.and.returnValue(of(makeCrmPage([makeCrmCustomer()])));
    modal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    TestBed.configureTestingModule({
      imports: [OpportunityDialogComponent],
      providers: [...provideTestTranslations(), { provide: CrmOpportunitiesApiService, useValue: api },
        { provide: CrmLeadsApiService, useValue: leads }, { provide: CrmCustomersApiService, useValue: customers },
        { provide: NgbActiveModal, useValue: modal }],
    });
    fixture = TestBed.createComponent(OpportunityDialogComponent);
    component = fixture.componentInstance;
    component.open({ board, owners: [{ id: 9, name: 'Beto' }], currentUser: me, ...context });
    fixture.detectChanges();
  }

  const text = (): string => (fixture.nativeElement as HTMLElement).textContent ?? '';

  it('converts between ISO and the local datetime input', () => {
    const iso = new Date(2026, 10, 25, 14, 30).toISOString();
    expect(toLocalInput(iso)).toBe('2026-11-25T14:30');
    expect(fromLocalInput('2026-11-25T14:30')).toBe(iso);
    expect(fromLocalInput('')).toBeNull();
    expect(toLocalInput(null)).toBe('');
  });

  it('defaults to the first stage and the current user and validates required fields', () => {
    setup();
    expect(component.form.controls.stageId.value).toBe('s-1');
    expect(component.form.controls.ownerId.value).toBe('7');
    expect(component.ownerOptions.map((o) => o.name)).toEqual(['Ana Admin', 'Beto']);
    component.form.controls.amount.setValue('-5');
    component.onSubmit();
    fixture.detectChanges();
    expect(api.create).not.toHaveBeenCalled();
    expect(text()).toContain('Elige un prospecto o un cliente.');
    expect(text()).toContain('El título es obligatorio.');
    expect(text()).toContain('Ingresa un importe positivo con hasta 2 decimales.');
  });

  it('searches leads or customers depending on the chosen kind', fakeAsync(() => {
    setup();
    component.contactSearch$.next('car');
    tick(250);
    expect(leads.list).toHaveBeenCalledWith({ search: 'car', pageSize: 20 });
    expect(component.contacts).toEqual([{ id: 'l-1', name: 'Carla Rojas', phone: '76543210' }]);
    component.form.controls.contactKind.setValue('customer');
    component.contactSearch$.next('ana');
    tick(250);
    expect(customers.list).toHaveBeenCalledWith({ search: 'ana', pageSize: 20 });
    expect(component.contacts[0].id).toBe('c-1');
  }));

  it('creates an opportunity for a lead in the chosen stage (AC-02)', () => {
    setup({ stageId: 's-2' });
    const saved = makeOpportunity();
    api.create.and.returnValue(of(saved));
    component.form.patchValue({
      contact: { id: 'l-1', name: 'Carla', phone: '7' }, title: ' Combo ', amount: '150.50', ownerId: '9',
      nextActionAt: '2026-11-25T14:30',
    });
    component.onSubmit();
    expect(api.create).toHaveBeenCalledOnceWith({
      boardId: 'b-1', stageId: 's-2', leadId: 'l-1', customerId: undefined, title: 'Combo', amount: '150.50',
      nextActionAt: fromLocalInput('2026-11-25T14:30'), ownerId: 9,
    });
    expect(modal.close).toHaveBeenCalledWith(saved);
  });

  it('shows a 409 board_has_no_stages as a warning without closing', () => {
    setup();
    api.create.and.returnValue(throwError(() => new CrmApiError('El tablero no tiene etapas activas.', 409, {}, 'board_has_no_stages')));
    component.form.patchValue({ contact: { id: 'l-1', name: 'Carla', phone: '7' }, title: 'Combo', amount: '10' });
    component.onSubmit();
    fixture.detectChanges();
    const alert = (fixture.nativeElement as HTMLElement).querySelector('[data-testid="opportunity-error"]');
    expect(alert?.classList).toContain('alert-warning');
    expect(alert?.textContent).toContain('El tablero no tiene etapas activas.');
    expect(modal.close).not.toHaveBeenCalled();
  });

  it('edits only the editable fields and sends the owner only when it changed', () => {
    const opportunity = makeOpportunity({ owner: me, nextActionAt: null });
    setup({ opportunity });
    expect(text()).toContain('Editar oportunidad');
    expect(text()).toContain('Carla Rojas');
    expect((fixture.nativeElement as HTMLElement).querySelector('#crm-opp-stage')).toBeNull();
    api.update.and.returnValue(of(opportunity));
    component.form.patchValue({ title: 'Combo grande', amount: '200' });
    component.onSubmit();
    expect(api.update).toHaveBeenCalledOnceWith('o-1', { title: 'Combo grande', amount: '200', nextActionAt: null });
    api.update.calls.reset();
    component.form.patchValue({ ownerId: '9' });
    component.onSubmit();
    expect(api.update).toHaveBeenCalledOnceWith('o-1', { title: 'Combo grande', amount: '200', nextActionAt: null, ownerId: 9 });
  });

  it('shows the server error under the owner field (400)', () => {
    setup();
    api.create.and.returnValue(throwError(() => new CrmApiError('x', 400, { ownerId: 'El responsable no pertenece a la empresa.' })));
    component.form.patchValue({ contact: { id: 'l-1', name: 'Carla', phone: '7' }, title: 'Combo', amount: '10' });
    component.onSubmit();
    fixture.detectChanges();
    expect(text()).toContain('El responsable no pertenece a la empresa.');
  });
});
