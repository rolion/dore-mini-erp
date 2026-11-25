import { provideTestTranslations } from '../../../../core/i18n/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { of, throwError } from 'rxjs';
import { CrmApiError } from '../../models/board';
import { CrmLeadConversion } from '../../models/lead';
import { CrmLeadsApiService } from '../../services/crm-leads-api.service';
import { makeLead } from '../../testing/crm-fixtures';
import { ConvertLeadDialogComponent } from './convert-lead-dialog.component';

describe('ConvertLeadDialogComponent', () => {
  let fixture: ComponentFixture<ConvertLeadDialogComponent>;
  let component: ConvertLeadDialogComponent;
  let api: jasmine.SpyObj<CrmLeadsApiService>;
  let modal: jasmine.SpyObj<NgbActiveModal>;
  const lead = { id: 'l-1', name: 'Carla', phone: '76543210' };
  const conversion: CrmLeadConversion = {
    lead: makeLead({ convertedCustomerId: 'c-2' }), customer: { id: 'c-2', name: 'Carla R.', phone: '+59176543210' }, created: false,
  };

  beforeEach(() => {
    api = jasmine.createSpyObj<CrmLeadsApiService>('CrmLeadsApiService', ['convert']);
    modal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    TestBed.configureTestingModule({
      imports: [ConvertLeadDialogComponent],
      providers: [...provideTestTranslations(), { provide: CrmLeadsApiService, useValue: api },
        { provide: NgbActiveModal, useValue: modal }],
    });
    fixture = TestBed.createComponent(ConvertLeadDialogComponent);
    component = fixture.componentInstance;
    component.open(lead);
    fixture.detectChanges();
  });

  const el = (): HTMLElement => fixture.nativeElement as HTMLElement;
  const confirmButton = (): HTMLButtonElement => el().querySelector('[data-testid="confirm-convert"]') as HTMLButtonElement;

  it('converts directly when the server finds a single match or none (AC-05)', () => {
    api.convert.and.returnValue(of(conversion));
    expect(el().textContent).toContain('se vinculará a ese cliente');
    confirmButton().click();
    expect(api.convert).toHaveBeenCalledOnceWith('l-1', undefined);
    expect(modal.close).toHaveBeenCalledWith(conversion);
  });

  it('asks to choose among several matching customers and sends the choice (409 multiple_customer_matches)', () => {
    api.convert.and.returnValue(throwError(() => new CrmApiError('Varios.', 409, {}, 'multiple_customer_matches', 0,
      [{ id: 'c-1', name: 'Carla A', phone: '+591765' }, { id: 'c-2', name: 'Carla B', phone: '+591765' }])));
    confirmButton().click();
    fixture.detectChanges();
    expect(modal.close).not.toHaveBeenCalled();
    expect(el().querySelector('[data-testid="multiple-matches"]')?.textContent).toContain('2 clientes');
    expect(el().querySelectorAll('[data-testid="candidate"]').length).toBe(2);
    expect(confirmButton().disabled).toBeTrue();
    api.convert.and.returnValue(of(conversion));
    (el().querySelectorAll('[data-testid="candidate"]')[1] as HTMLInputElement).click();
    fixture.detectChanges();
    expect(confirmButton().disabled).toBeFalse();
    confirmButton().click();
    expect(api.convert).toHaveBeenCalledWith('l-1', 'c-2');
    expect(modal.close).toHaveBeenCalledWith(conversion);
  });

  it('keeps the dialog open with a warning on another conflict', () => {
    api.convert.and.returnValue(throwError(() => new CrmApiError('El cliente no está activo.', 409, {}, 'customer_inactive')));
    confirmButton().click();
    fixture.detectChanges();
    const alert = el().querySelector('[data-testid="convert-error"]');
    expect(alert?.classList).toContain('alert-warning');
    expect(alert?.textContent).toContain('El cliente no está activo.');
    expect(modal.close).not.toHaveBeenCalled();
  });
});
