import { provideTestTranslations } from '../../../../core/i18n/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { of, throwError } from 'rxjs';
import { CrmApiError } from '../../models/board';
import { CrmLeadsApiService } from '../../services/crm-leads-api.service';
import { makeLead } from '../../testing/crm-fixtures';
import { LeadDialogComponent } from './lead-dialog.component';

describe('LeadDialogComponent', () => {
  let fixture: ComponentFixture<LeadDialogComponent>;
  let component: LeadDialogComponent;
  let api: jasmine.SpyObj<CrmLeadsApiService>;
  let modal: jasmine.SpyObj<NgbActiveModal>;

  beforeEach(() => {
    api = jasmine.createSpyObj<CrmLeadsApiService>('CrmLeadsApiService', ['create', 'update']);
    modal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    TestBed.configureTestingModule({
      imports: [LeadDialogComponent],
      providers: [...provideTestTranslations(), { provide: CrmLeadsApiService, useValue: api },
        { provide: NgbActiveModal, useValue: modal }],
    });
    fixture = TestBed.createComponent(LeadDialogComponent);
    component = fixture.componentInstance;
  });

  const text = (): string => (fixture.nativeElement as HTMLElement).textContent ?? '';

  it('requires the name and validates the email', () => {
    fixture.detectChanges();
    component.form.controls.email.setValue('no-es-correo');
    component.onSubmit();
    fixture.detectChanges();
    expect(api.create).not.toHaveBeenCalled();
    expect(text()).toContain('El nombre es obligatorio.');
    expect(text()).toContain('El correo no es válido.');
  });

  it('creates a lead with trimmed values and closes with it (AC-01)', () => {
    const saved = makeLead();
    api.create.and.returnValue(of(saved));
    fixture.detectChanges();
    component.form.setValue({ name: ' Carla ', phone: ' 76543210 ', email: '' });
    component.onSubmit();
    expect(api.create).toHaveBeenCalledOnceWith({ name: 'Carla', phone: '76543210', email: '' });
    expect(modal.close).toHaveBeenCalledWith(saved);
  });

  it('edits an existing lead and shows server field errors without closing', () => {
    component.edit(makeLead({ id: 'l-9', name: 'Carla' }));
    fixture.detectChanges();
    expect(text()).toContain('Editar prospecto');
    api.update.and.returnValue(throwError(() => new CrmApiError('x', 400, { phone: 'Teléfono inválido para Bolivia.' })));
    component.form.controls.phone.setValue('123');
    component.onSubmit();
    fixture.detectChanges();
    expect(api.update).toHaveBeenCalledWith('l-9', { name: 'Carla', phone: '123', email: 'carla@ejemplo.com' });
    expect(text()).toContain('Teléfono inválido para Bolivia.');
    expect(modal.close).not.toHaveBeenCalled();
  });
});
