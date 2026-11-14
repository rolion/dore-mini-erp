import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { RegularizationError, toSummary } from '../../models/regularization';
import { AccountingApiService } from '../../services/accounting-api.service';
import { RegularizationApiService } from '../../services/regularization-api.service';
import { makeSummaryDto } from '../../testing/regularization-fixtures';
import { RegularizationComponent } from './regularization.component';

describe('RegularizationComponent', () => {
  const methods = [{ code: 'CASH', label: 'Efectivo', isActive: true, account: null }, { code: 'QR', label: 'QR', isActive: true, account: null }];
  const accounts = [
    { id: 'a-1', name: 'Caja', currency: 'BOB', isActive: true },
    { id: 'a-9', name: 'Dólares', currency: 'USD', isActive: true },
  ];

  function setup(modalResult: Promise<boolean> = Promise.resolve(true)) {
    const api = jasmine.createSpyObj<AccountingApiService>('AccountingApiService', ['listMethods', 'listAccounts']);
    api.listMethods.and.returnValue(of(methods));
    api.listAccounts.and.returnValue(of(accounts));
    const regularization = jasmine.createSpyObj<RegularizationApiService>('RegularizationApiService', ['preview', 'apply']);
    regularization.preview.and.returnValue(of(toSummary(makeSummaryDto())));
    regularization.apply.and.returnValue(of(toSummary(makeSummaryDto({ mode: 'apply', groups: [
      { status: 'created', origin: 'PRODUCT', account_id: 'a-1', account: 'Caja', currency: 'BOB', count: 3, amount: '175.00' },
    ], details: [] }))));
    const dialog: { componentInstance: Record<string, unknown>; result: Promise<boolean> } = { componentInstance: {}, result: modalResult };
    const modal = jasmine.createSpyObj<NgbModal>('NgbModal', ['open']);
    modal.open.and.returnValue(dialog as never);
    TestBed.configureTestingModule({
      imports: [RegularizationComponent],
      providers: [...provideTestTranslations(), provideRouter([]),
        { provide: AccountingApiService, useValue: api }, { provide: RegularizationApiService, useValue: regularization },
        { provide: NgbModal, useValue: modal }],
    });
    const fixture = TestBed.createComponent(RegularizationComponent);
    fixture.detectChanges();
    return { fixture, component: fixture.componentInstance, regularization, modal, dialog, el: fixture.nativeElement as HTMLElement };
  }

  const click = (el: HTMLElement, id: string) => (el.querySelector(`[data-testid="${id}"]`) as HTMLButtonElement).click();

  it('starts with no rules and offers only BOB accounts, never a default mapping (AC-15, UI-02)', () => {
    const { component, el, fixture } = setup();
    expect(el.querySelector('[data-testid="no-rules"]')).not.toBeNull();
    expect(el.querySelector('[data-testid="summary"]')).toBeNull();
    click(el, 'add-rule');
    fixture.detectChanges();
    const options = Array.from(el.querySelectorAll('[data-testid="rule"] select')[1].querySelectorAll('option')).map((o) => o.textContent?.trim());
    expect(options).toContain('Caja');
    expect(options).not.toContain('Dólares');
    expect(component.rules.at(0).getRawValue().accountId).toBe('');
  });

  it('previews the entered mapping and shows the summary by origin and account (AC-15, UI-03)', () => {
    const { component, el, fixture, regularization } = setup();
    click(el, 'add-rule');
    component.rules.at(0).patchValue({ method: 'CASH', accountId: 'a-1' });
    fixture.detectChanges();
    click(el, 'preview');
    fixture.detectChanges();
    expect(regularization.preview).toHaveBeenCalledWith({ date_from: null, date_to: null, mapping: { CASH: [{ account_id: 'a-1' }] } });
    expect(el.querySelectorAll('[data-testid="group"]').length).toBe(3);
    expect(el.querySelector('[data-testid="summary"]')?.textContent).toContain('no se ha escrito nada');
    expect(el.querySelector('[data-testid="absent"]')?.textContent).toContain('Autor');
    expect(el.querySelectorAll('[data-testid="detail"]').length).toBe(1);
    expect(regularization.apply).not.toHaveBeenCalled();
  });

  it('applies only after confirmation and shows the result with a link to the entries (AC-16)', async () => {
    const { el, fixture, regularization, modal, dialog } = setup();
    click(el, 'preview');
    fixture.detectChanges();
    click(el, 'apply');
    await fixture.whenStable();
    fixture.detectChanges();
    expect(modal.open).toHaveBeenCalled();
    expect(dialog.componentInstance['count']).toBe(3);
    expect(regularization.apply).toHaveBeenCalledTimes(1);
    expect(el.querySelector('[data-testid="result"]')?.textContent).toContain('3 creadas');
    expect(el.querySelector('[data-testid="apply"]')).toBeNull();
  });

  it('does not apply when the confirmation is dismissed (AC-16)', async () => {
    const { el, fixture, regularization } = setup(Promise.reject(new Error('dismissed')));
    click(el, 'preview');
    fixture.detectChanges();
    click(el, 'apply');
    await fixture.whenStable();
    expect(regularization.apply).not.toHaveBeenCalled();
  });

  it('disables apply when the form changed after previewing or when nothing is missing (AC-16)', () => {
    const { component, el, fixture, regularization } = setup();
    click(el, 'preview');
    fixture.detectChanges();
    expect((el.querySelector('[data-testid="apply"]') as HTMLButtonElement).disabled).toBeFalse();
    component.form.controls.dateFrom.setValue('2026-03-01');
    fixture.detectChanges();
    expect((el.querySelector('[data-testid="apply"]') as HTMLButtonElement).disabled).toBeTrue();
    expect(el.querySelector('[data-testid="stale"]')).not.toBeNull();

    regularization.preview.and.returnValue(of(toSummary(makeSummaryDto({ groups: [
      { status: 'existing', origin: 'PRODUCT', account_id: 'a-1', account: 'Caja', currency: 'BOB', count: 1, amount: '10.00' }], details: [] }))));
    click(el, 'preview');
    fixture.detectChanges();
    expect((el.querySelector('[data-testid="apply"]') as HTMLButtonElement).disabled).toBeTrue();
    expect(el.querySelector('[data-testid="no-missing"]')).not.toBeNull();
  });

  it('shows the empty state, validation errors and the in-progress conflict (AC-17, UI-05)', () => {
    const { component, el, fixture, regularization } = setup();
    regularization.preview.and.returnValue(of(toSummary(makeSummaryDto({ total_payments: 0, groups: [], details: [], absent_fields: {} }))));
    click(el, 'preview');
    fixture.detectChanges();
    expect(el.querySelector('[data-testid="empty"]')).not.toBeNull();

    regularization.preview.and.returnValue(throwError(() => new RegularizationError('Revisa', 400, ['CASH: la cuenta no existe en la empresa.'])));
    click(el, 'preview');
    fixture.detectChanges();
    expect(el.querySelector('[data-testid="errors"]')?.textContent).toContain('la cuenta no existe');

    regularization.apply.and.returnValue(throwError(() => new RegularizationError('En curso', 409, [], 'regularization_in_progress')));
    regularization.preview.and.returnValue(of(toSummary(makeSummaryDto())));
    click(el, 'preview');
    fixture.detectChanges();
    component.confirmApply();
    return Promise.resolve().then(() => fixture.whenStable()).then(() => {
      fixture.detectChanges();
      expect(el.querySelector('[data-testid="errors"]')?.classList).toContain('alert-warning');
    });
  });

  it('clears an applied summary when a new preview fails, so no false «nothing written» notice remains (REV-03)', async () => {
    const { el, fixture, regularization } = setup();
    click(el, 'preview');
    fixture.detectChanges();
    click(el, 'apply');
    await fixture.whenStable();
    fixture.detectChanges();
    expect(el.querySelector('[data-testid="result"]')).not.toBeNull();

    regularization.preview.and.returnValue(throwError(() => new RegularizationError('Sin conexión', 0)));
    click(el, 'preview');
    fixture.detectChanges();
    expect(el.querySelector('[data-testid="summary"]')).toBeNull();
    expect(el.querySelector('[data-testid="errors"]')).not.toBeNull();
  });

  it('warns about half-filled rules instead of dropping them silently, and previews without rules (REV-04)', () => {
    const { component, el, fixture, regularization } = setup();
    click(el, 'preview');
    fixture.detectChanges();
    expect(regularization.preview).toHaveBeenCalledWith({ date_from: null, date_to: null, mapping: {} });

    click(el, 'add-rule');
    component.rules.at(0).patchValue({ method: 'CASH' });
    fixture.detectChanges();
    expect(el.querySelector('[data-testid="incomplete-rules"]')).not.toBeNull();
    expect((el.querySelector('[data-testid="preview"]') as HTMLButtonElement).disabled).toBeTrue();
    regularization.preview.calls.reset();
    component.preview();
    expect(regularization.preview).not.toHaveBeenCalled();

    component.rules.at(0).patchValue({ accountId: 'a-1' });
    fixture.detectChanges();
    expect(el.querySelector('[data-testid="incomplete-rules"]')).toBeNull();
  });

  it('blocks previewing an inverted period (AC-14)', () => {
    const { component, el, fixture, regularization } = setup();
    component.form.patchValue({ dateFrom: '2026-05-01', dateTo: '2026-01-01' });
    fixture.detectChanges();
    expect(el.querySelector('[data-testid="range-error"]')).not.toBeNull();
    expect((el.querySelector('[data-testid="preview"]') as HTMLButtonElement).disabled).toBeTrue();
    component.preview();
    expect(regularization.preview).not.toHaveBeenCalled();
  });
});
