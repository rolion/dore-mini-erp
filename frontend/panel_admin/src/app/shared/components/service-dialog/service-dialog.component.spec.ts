import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Component, ViewChild } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { CommitmentLine, ServiceRendered } from '../../models/receivable';
import { ServiceDialogComponent } from './service-dialog.component';

const LINE: CommitmentLine = {
  line_id: 'l2', description: 'Corona', piece: '18', decision: 'accepted', proposed: '200.00', accepted: '200.00',
  paid: '0.00', balance: '200.00', collectible: true, rendered: false, service_date: null, can_render: true,
};

@Component({
  imports: [ServiceDialogComponent],
  template: `<app-service-dialog #dlg kind="quotation" number="PRO-000001" (rendered)="result = $event" />`,
})
class HostComponent {
  @ViewChild('dlg', { static: true }) dialog!: ServiceDialogComponent;
  result: ServiceRendered | null = null;
}

describe('ServiceDialogComponent', () => {
  let http: HttpTestingController;

  function create() {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([]), ...provideTestTranslations()],
    });
    http = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
    const dialog = fixture.componentInstance.dialog;
    dialog.open(LINE);
    fixture.detectChanges();
    return { fixture, dialog };
  }

  afterEach(() => http.verify());

  it('muestra el tratamiento, su importe, la advertencia de que no se deshace y la fecha de hoy (UI-02)', () => {
    const { fixture, dialog } = create();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Corona');
    expect(text).toContain('Bs 200.00');
    expect(text).toContain('No se puede deshacer');
    expect(dialog.form.controls.service_date.value).toBe(dialog.today);
    expect(dialog.canConfirm).toBeTrue();
  });

  it('confirma con el tratamiento y la fecha, emite el resultado y no deja el diálogo guardando (AC-13)', () => {
    const { fixture, dialog } = create();
    dialog.form.controls.service_date.setValue('2026-11-10');
    dialog.confirm();
    expect(dialog.saving).toBeTrue();
    const request = http.expectOne((req) => req.url.endsWith('/commitments/quotation/PRO-000001/services/'));
    expect(request.request.body).toEqual({ line_id: 'l2', service_date: '2026-11-10' });
    const body = { service: { id: 's1', description: 'Corona' }, replayed: false } as ServiceRendered;
    request.flush(body);
    fixture.detectChanges();
    expect(fixture.componentInstance.result).toEqual(body);
    expect(dialog.saving).toBeFalse();
  });

  it('un 409 por configuración incompleta conserva el diálogo y lista lo que falta con enlace a la configuración (UI-03)', () => {
    const { fixture, dialog } = create();
    dialog.confirm();
    http.expectOne((req) => req.url.endsWith('/services/')).flush(
      { detail: 'Falta la cuenta de Ingresos por servicios.', code: 'posting_configuration_missing',
        issues: [{ code: 'account_missing', role: 'SERVICE_INCOME', subject: 'Ingresos por servicios', message: 'Falta la cuenta de Ingresos por servicios.' }] },
      { status: 409, statusText: 'Conflict' });
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    expect(dialog.failure?.code).toBe('posting_configuration_missing');
    expect(root.querySelector('[data-testid="alert-posting-issues"]')?.textContent).toContain('Ingresos por servicios');
    expect(root.querySelector('[data-testid="link-posting-settings"]')?.getAttribute('href')).toContain('/pocketbiz/receivables/settings');
    expect(fixture.componentInstance.result).toBeNull();
  });

  it('otros 409 muestran el mensaje del servidor sin lista de faltantes', () => {
    const { fixture, dialog } = create();
    dialog.confirm();
    http.expectOne((req) => req.url.endsWith('/services/')).flush(
      { detail: 'El tratamiento tiene cobros registrados sin asiento contable.', code: 'service_has_unposted_payments' },
      { status: 409, statusText: 'Conflict' });
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    expect(root.querySelector('.alert-danger')?.textContent).toContain('sin asiento contable');
    expect(root.querySelector('[data-testid="alert-posting-issues"]')).toBeNull();
  });
});
