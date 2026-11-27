import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { WhatsappApiError, WhatsappConnection, WhatsappTemplate } from '../../models/whatsapp';
import { WhatsappApiService } from '../../services/whatsapp-api.service';
import { WhatsappIntegrationComponent } from './whatsapp-integration.component';

const connection = (extra: Partial<WhatsappConnection> = {}): WhatsappConnection => ({
  configured: true, webhookUrl: 'https://x/hook/', wabaId: '9', phoneNumberId: '111', displayPhone: '', secretRef: 'WHATSAPP_T',
  appSecretRef: 'WHATSAPP_A', verifyToken: 'verify-1', status: 'active', statusReason: '', ...extra,
});
const template = (status: string): WhatsappTemplate => ({ id: `t-${status}`, name: `n-${status}`, language: 'es', category: 'UTILITY', status, syncedAt: null });

describe('WhatsappIntegrationComponent', () => {
  let fixture: ComponentFixture<WhatsappIntegrationComponent>;
  let api: jasmine.SpyObj<WhatsappApiService>;
  const el = () => fixture.nativeElement as HTMLElement;

  const setup = (conn: WhatsappConnection, templates: WhatsappTemplate[] = []) => {
    api.getConnection.and.returnValue(of(conn));
    api.listTemplates.and.returnValue(of(templates));
    fixture = TestBed.createComponent(WhatsappIntegrationComponent);
    fixture.detectChanges();
  };

  beforeEach(() => {
    api = jasmine.createSpyObj<WhatsappApiService>('WhatsappApiService', ['getConnection', 'saveConnection', 'listTemplates', 'syncTemplates', 'sendTestMessage']);
    TestBed.configureTestingModule({
      imports: [WhatsappIntegrationComponent],
      providers: [...provideTestTranslations(), provideRouter([]), { provide: WhatsappApiService, useValue: api }],
    });
  });

  it('shows the empty state and hides test and templates when nothing is configured (UI-02)', () => {
    setup(connection({ configured: false, status: 'none', wabaId: '', phoneNumberId: '', secretRef: '', appSecretRef: '' }));
    expect(el().querySelector('#whatsapp-status')?.textContent).toContain('Sin configurar');
    expect(el().querySelector('#wa-webhook')).toBeNull();
    expect(el().querySelector('#wa-template')).toBeNull();
  });

  it('rejects secret names without the WHATSAPP_ prefix and does not call the API', () => {
    setup(connection({ configured: false, status: 'none' }));
    component().form.setValue({ wabaId: '9', phoneNumberId: '1', displayPhone: '', secretRef: 'SECRET_KEY', appSecretRef: 'WHATSAPP_A' });
    component().submit();
    expect(api.saveConnection).not.toHaveBeenCalled();
    expect(component().form.controls.secretRef.invalid).toBeTrue();
  });

  it('asks for confirmation before changing the sender and saves once confirmed', () => {
    setup(connection());
    api.saveConnection.and.returnValue(of(connection({ phoneNumberId: '222' })));
    component().form.patchValue({ phoneNumberId: '222' });
    component().submit();
    expect(component().confirmingChange).toBeTrue();
    expect(api.saveConnection).not.toHaveBeenCalled();
    component().submit(true);
    expect(api.saveConnection).toHaveBeenCalledTimes(1);
    expect(component().saved).toBeTrue();
  });

  it('shows server field errors', () => {
    setup(connection({ configured: false, status: 'none' }));
    api.saveConnection.and.returnValue(throwError(() => new WhatsappApiError('x', 400, null, { phoneNumberId: 'Este número ya está conectado' })));
    component().form.setValue({ wabaId: '9', phoneNumberId: '1', displayPhone: '', secretRef: 'WHATSAPP_T', appSecretRef: 'WHATSAPP_A' });
    component().submit();
    fixture.detectChanges();
    expect(el().textContent).toContain('Este número ya está conectado');
  });

  it('lists templates with badges and offers only approved ones for the test (UI-01)', () => {
    setup(connection(), [template('APPROVED'), template('REJECTED'), template('PAUSED')]);
    expect(el().querySelectorAll('tbody tr').length).toBe(3);
    expect(el().querySelector('.badge-outline.col-red')).not.toBeNull();
    expect(el().querySelectorAll('#wa-template option').length).toBe(2); // placeholder + aprobada
  });

  it('sends the test message and reports an error from the server', () => {
    setup(connection(), [template('APPROVED')]);
    component().testForm.setValue({ to: '76543210', templateId: 't-APPROVED' });
    api.sendTestMessage.and.returnValue(of({ id: 'm', status: 'queued' }));
    component().sendTest();
    expect(component().testResult?.ok).toBeTrue();
    api.sendTestMessage.and.returnValue(throwError(() => new WhatsappApiError('Plantilla no aprobada', 409, 'template_not_approved')));
    component().sendTest();
    expect(component().testResult).toEqual({ ok: false, message: 'Plantilla no aprobada' });
  });

  it('disables the test when the connection is not active', () => {
    setup(connection({ status: 'error', statusReason: 'token_expired' }), [template('APPROVED')]);
    expect(component().canSendTest).toBeFalse();
    expect(el().querySelector('.alert-warning')?.textContent).toContain('Meta rechazó el token');
  });

  it('syncs templates', () => {
    setup(connection());
    api.syncTemplates.and.returnValue(of([template('APPROVED')]));
    api.getConnection.and.returnValue(of(connection()));
    component().sync();
    expect(component().templates.length).toBe(1);
  });

  function component(): WhatsappIntegrationComponent {
    return fixture.componentInstance;
  }
});
