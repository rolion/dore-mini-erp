import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { CrmApiError } from '../../models/board';
import { CrmActivitiesApiService } from '../../services/crm-activities-api.service';
import { CrmCustomersApiService } from '../../services/crm-customers-api.service';
import { CrmLeadsApiService } from '../../services/crm-leads-api.service';
import { CrmOpportunitiesApiService } from '../../services/crm-opportunities-api.service';
import { makeCrmCustomer, makeCrmPage, makeLead, makeOpportunity } from '../../testing/crm-fixtures';
import { TrackingCardDialogComponent, TrackingContactOption } from './tracking-card-dialog.component';

describe('TrackingCardDialogComponent', () => {
  function setup() {
    const api = jasmine.createSpyObj<CrmOpportunitiesApiService>('CrmOpportunitiesApiService', ['create', 'update']);
    const leads = jasmine.createSpyObj<CrmLeadsApiService>('CrmLeadsApiService', ['list']);
    leads.list.and.returnValue(of({ count: 1, results: [makeLead()] }));
    const customers = jasmine.createSpyObj<CrmCustomersApiService>('CrmCustomersApiService', ['list']);
    customers.list.and.returnValue(of(makeCrmPage([makeCrmCustomer()])));
    const activities = jasmine.createSpyObj<CrmActivitiesApiService>('CrmActivitiesApiService', ['list', 'create']);
    activities.list.and.returnValue(of({ count: 0, results: [] }));
    const modal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    TestBed.configureTestingModule({
      imports: [TrackingCardDialogComponent],
      providers: [...provideTestTranslations(), { provide: CrmOpportunitiesApiService, useValue: api },
        { provide: CrmLeadsApiService, useValue: leads }, { provide: CrmCustomersApiService, useValue: customers },
        { provide: NgbActiveModal, useValue: modal },
        { provide: CrmActivitiesApiService, useValue: activities }],
    });
    const fixture = TestBed.createComponent(TrackingCardDialogComponent);
    fixture.componentInstance.open({ boardId: 'b-1', stageId: 's-2' });
    fixture.detectChanges();
    return { fixture, component: fixture.componentInstance, api, leads, customers, modal };
  }

  const customerOption: TrackingContactOption = {
    key: 'customer:c-1', id: 'c-1', kind: 'customer', name: 'Ana', phone: '7', group: 'Clientes',
  };
  const leadOption: TrackingContactOption = { key: 'lead:l-1', id: 'l-1', kind: 'lead', name: 'Carla', phone: '7', group: 'Prospectos' };

  it('requires name and customer or prospect; description is optional (AC-06)', () => {
    const { component, api } = setup();
    component.onSubmit();
    expect(api.create).not.toHaveBeenCalled();
    component.form.patchValue({ name: 'Llamar', contact: customerOption });
    expect(component.form.valid).toBeTrue();
  });

  it('offers customers and prospects of the company in one list, grouped (AC-06)', fakeAsync(() => {
    const { component, customers, leads } = setup();
    tick(300);
    expect(customers.list).toHaveBeenCalled();
    expect(leads.list).toHaveBeenCalled();
    expect(component.contacts.map((c) => [c.kind, c.group])).toEqual([['customer', 'Clientes'], ['lead', 'Prospectos']]);
  }));

  it('creates the card in the origin column linked to a customer, without amount (AC-06)', () => {
    const { component, api, modal } = setup();
    const saved = makeOpportunity({ title: 'Llamar' });
    api.create.and.returnValue(of(saved));
    component.form.patchValue({ name: ' Llamar ', contact: customerOption, description: ' Quiere precio ' });
    component.onSubmit();
    expect(api.create).toHaveBeenCalledOnceWith({
      boardId: 'b-1', stageId: 's-2', leadId: undefined, customerId: 'c-1', title: 'Llamar', description: 'Quiere precio',
    });
    expect(modal.close).toHaveBeenCalledOnceWith(saved);
  });

  it('links a prospect through leadId', () => {
    const { component, api } = setup();
    api.create.and.returnValue(of(makeOpportunity()));
    component.form.patchValue({ name: 'Seguir', contact: leadOption });
    component.onSubmit();
    expect(api.create.calls.mostRecent().args[0].leadId).toBe('l-1');
    expect(api.create.calls.mostRecent().args[0].customerId).toBeUndefined();
  });

  it('shows a server conflict and keeps the dialog open', () => {
    const { fixture, component, api, modal } = setup();
    api.create.and.returnValue(throwError(() => new CrmApiError('El tablero está archivado.', 409)));
    component.form.patchValue({ name: 'Seguir', contact: leadOption });
    component.onSubmit();
    fixture.detectChanges();
    expect(modal.close).not.toHaveBeenCalled();
    expect((fixture.nativeElement as HTMLElement).querySelector('[data-testid="dialog-error"]')?.textContent)
      .toContain('archivado');
  });

  describe('card record (view and edit)', () => {
    const card = makeOpportunity({ id: 'o-9', title: 'Llamar', description: 'Quiere precio' });

    function openCard() {
      const ctx = setup();
      ctx.component.open({ boardId: 'b-1', stageId: 's-2', card });
      ctx.fixture.detectChanges();
      return ctx;
    }

    it('shows the card values read-only: title, customer and description', () => {
      const { fixture, component } = openCard();
      const el = fixture.nativeElement as HTMLElement;
      expect(component.isEdit).toBeTrue();
      expect(el.querySelector('[data-testid="info-title"]')?.textContent).toContain('Llamar');
      expect(el.querySelector('[data-testid="info-contact"]')?.textContent).toBeTruthy();
      expect(el.querySelector('[data-testid="info-description"]')?.textContent).toContain('Quiere precio');
      expect(el.querySelector('[data-testid="close-card"]')).not.toBeNull();
    });

    it('edits name and description only after pressing Edit, keeping the customer fixed', () => {
      const { fixture, component, api, modal } = openCard();
      ((fixture.nativeElement as HTMLElement).querySelector('[data-testid="edit-card"]') as HTMLButtonElement).click();
      fixture.detectChanges();
      expect(component.editing).toBeTrue();
      expect(component.form.controls.contact.disabled).toBeTrue();
      api.update.and.returnValue(of({ ...card, title: 'Nuevo' }));
      component.form.patchValue({ name: ' Nuevo ', description: ' Otra ' });
      component.onSubmit();
      expect(api.update).toHaveBeenCalledOnceWith('o-9', { title: 'Nuevo', description: 'Otra' });
      expect(api.create).not.toHaveBeenCalled();
      expect(modal.close).toHaveBeenCalled();
    });

    it('cancelling the edit restores the values', () => {
      const { component } = openCard();
      component.startEdit();
      component.form.patchValue({ name: 'Cambiado' });
      component.cancelEdit();
      expect(component.editing).toBeFalse();
      expect(component.form.controls.name.value).toBe('Llamar');
    });

    it('shows the activities column only on an existing card', () => {
      const { fixture, component } = setup();
      const el = fixture.nativeElement as HTMLElement;
      expect(el.querySelector('[data-testid="activity-column"]')).toBeNull();
      component.open({ boardId: 'b-1', stageId: 's-2', card });
      fixture.detectChanges();
      expect(el.querySelector('[data-testid="activity-column"] app-crm-activity-panel')).not.toBeNull();
    });
  });
});
