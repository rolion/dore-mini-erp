import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../../../environments/environment';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { WhatsappApiError } from '../models/whatsapp';
import { WhatsappApiService } from './whatsapp-api.service';

describe('WhatsappApiService', () => {
  let api: WhatsappApiService;
  let http: HttpTestingController;
  const base = `${environment.apiUrl}/messaging/whatsapp/`;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting()] });
    api = TestBed.inject(WhatsappApiService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('maps an unconfigured connection (API-03)', () => {
    let status = '';
    api.getConnection().subscribe((c) => (status = c.status));
    http.expectOne(`${base}connection/`).flush({ configured: false, webhook_url: 'https://x/hook/' });
    expect(status).toBe('none');
  });

  it('saves trimmed fields and never sends a secret value (API-03, AC-09)', () => {
    api.saveConnection({ wabaId: ' 9 ', phoneNumberId: '111', displayPhone: '', secretRef: ' WHATSAPP_T ', appSecretRef: 'WHATSAPP_A' }).subscribe();
    const req = http.expectOne(`${base}connection/`);
    expect(req.request.method).toBe('PUT');
    expect(req.request.body).toEqual({ waba_id: '9', phone_number_id: '111', display_phone: '', secret_ref: 'WHATSAPP_T', app_secret_ref: 'WHATSAPP_A' });
    req.flush({ configured: true, webhook_url: 'u', waba_id: '9', phone_number_id: '111', status: 'active', verify_token: 'v' });
  });

  it('turns a 400 into field errors and a 409 code into a translated message (API-04)', () => {
    const errors: WhatsappApiError[] = [];
    api.saveConnection({ wabaId: '9', phoneNumberId: '1', displayPhone: '', secretRef: 'X', appSecretRef: 'Y' }).subscribe({ error: (e) => errors.push(e) });
    http.expectOne(`${base}connection/`).flush({ secret_ref: ['Usa WHATSAPP_'] }, { status: 400, statusText: 'Bad Request' });
    api.sendTestMessage(' 76543210 ', 't-1').subscribe({ error: (e) => errors.push(e) });
    const req = http.expectOne(`${base}test-message/`);
    expect(req.request.body).toEqual({ to: '76543210', template_id: 't-1' });
    req.flush({ detail: 'x', code: 'template_not_approved' }, { status: 409, statusText: 'Conflict' });
    expect(errors[0].fieldErrors['secretRef']).toBe('Usa WHATSAPP_');
    expect(errors[1].code).toBe('template_not_approved');
    expect(errors[1].message).not.toContain('SETTINGS.');
  });

  it('lists and syncs templates (API-05)', () => {
    const dto = { id: 't', name: 'hello', language: 'en_US', category: 'UTILITY', status: 'APPROVED', synced_at: null };
    let names: string[] = [];
    api.listTemplates().subscribe((t) => (names = t.map((x) => x.name)));
    http.expectOne(`${base}templates/`).flush({ results: [dto] });
    expect(names).toEqual(['hello']);
    api.syncTemplates().subscribe();
    const req = http.expectOne(`${base}templates/sync/`);
    expect(req.request.method).toBe('POST');
    req.flush({ results: [] });
  });

  it('reports a network failure', () => {
    let error: WhatsappApiError | null = null;
    api.getConnection().subscribe({ error: (e) => (error = e) });
    http.expectOne(`${base}connection/`).error(new ProgressEvent('error'));
    expect((error as WhatsappApiError | null)?.status).toBe(0);
  });
});
