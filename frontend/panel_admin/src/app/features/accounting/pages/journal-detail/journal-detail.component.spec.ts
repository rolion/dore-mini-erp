import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { Observable, of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { AccountingApiError } from '../../models/accounting';
import { JournalEntryDetail } from '../../models/journal';
import { JournalApiService } from '../../services/journal-api.service';
import { makeJournalDetail } from '../../testing/journal-fixtures';
import { JournalDetailComponent } from './journal-detail.component';

describe('JournalDetailComponent', () => {
  function create(get: Observable<JournalEntryDetail>, modal: Partial<NgbModal> = {}) {
    const api = jasmine.createSpyObj<JournalApiService>('JournalApiService', ['get']);
    api.get.and.returnValue(get);
    TestBed.configureTestingModule({
      imports: [JournalDetailComponent],
      providers: [
        ...provideTestTranslations(), provideRouter([]),
        { provide: JournalApiService, useValue: api },
        { provide: NgbModal, useValue: modal },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: 'j-1' }), queryParamMap: convertToParamMap({}) }, paramMap: of(convertToParamMap({ id: 'j-1' })) } },
      ],
    });
    const fixture = TestBed.createComponent(JournalDetailComponent);
    fixture.detectChanges();
    return { fixture, api, el: fixture.nativeElement as HTMLElement };
  }

  it('shows lines, totals, user and period, with no edit or delete action (AC-05, AC-06)', () => {
    const { el, api } = create(of(makeJournalDetail()));
    expect(api.get).toHaveBeenCalledWith('j-1');
    expect(el.querySelectorAll('[data-testid="line"]').length).toBe(3);
    expect(el.querySelector('[data-testid="total-debit"]')?.textContent).toContain('500.00');
    expect(el.querySelector('[data-testid="user"]')?.textContent).toContain('Ana');
    expect(el.querySelector('[data-testid="period"]')?.textContent).toContain('Q2');
    expect(el.textContent).toContain('111001');
    expect(el.querySelector('.btn-danger')).toBeNull();
    expect(el.querySelector('[data-testid="immutable-note"]')).not.toBeNull();
    expect(el.querySelector('[data-testid="reverse"]')).not.toBeNull();
  });

  it('links an automatic entry to its source only when available and never allows edits (AC-04)', () => {
    const linked = create(of(makeJournalDetail({ source: 'AUTOMATIC', origin: { kind: 'PRODUCT', id: 'o-1', available: true } }))).el;
    expect(linked.querySelector('[data-testid="origin-link"]')?.getAttribute('href')).toContain('/sales/orders/o-1');
    TestBed.resetTestingModule();
    const unavailable = create(of(makeJournalDetail({ source: 'AUTOMATIC', origin: { kind: 'EXPENSE', id: 'x', available: false } }))).el;
    expect(unavailable.querySelector('[data-testid="origin-link"]')).toBeNull();
    expect(unavailable.querySelector('[data-testid="origin-text"]')?.textContent).toContain('EXPENSE');
  });

  it('links an original and its reversal both ways and hides Reverse (AC-05, AC-07)', () => {
    const original = create(of(makeJournalDetail({ reversed_by_id: 'j-2', can_reverse: false }))).el;
    expect(original.querySelector('[data-testid="reversal-link"]')).not.toBeNull();
    expect(original.querySelector('[data-testid="reverse"]')).toBeNull();
    expect(original.querySelector('[data-testid="cannot-reverse"]')).not.toBeNull();
    TestBed.resetTestingModule();
    const reversal = create(of(makeJournalDetail({ is_reversal: true, reverses_id: 'j-1', reversal_reason: 'Error', can_reverse: false }))).el;
    expect(reversal.querySelector('[data-testid="original-link"]')).not.toBeNull();
    expect(reversal.querySelector('[data-testid="reason"]')?.textContent).toContain('Error');
    expect(reversal.querySelector('[data-testid="reverse"]')).toBeNull();
  });

  it('opens the reversal dialog and reloads after reversing (AC-07)', () => {
    const reversal = makeJournalDetail({ id: 'j-2', reverses_id: 'j-1' });
    const instance = { init: jasmine.createSpy('init') };
    const modal = { open: jasmine.createSpy('open').and.returnValue({ componentInstance: instance, result: Promise.resolve(reversal) }) };
    const { el, api, fixture } = create(of(makeJournalDetail()), modal);
    (el.querySelector('[data-testid="reverse"]') as HTMLButtonElement).click();
    expect(modal.open).toHaveBeenCalled();
    expect(instance.init).toHaveBeenCalled();
    return fixture.whenStable().then(() => {
      fixture.detectChanges();
      expect(api.get).toHaveBeenCalledTimes(2);
      expect(el.querySelector('[data-testid="reversal-created-link"]')?.getAttribute('href')).toContain('j-2');
    });
  });

  it('shows a not-found error without retry and a retry for other errors', () => {
    const missing = create(throwError(() => new AccountingApiError('No existe', 404))).el;
    expect(missing.querySelector('[data-testid="detail-error"]')).not.toBeNull();
    expect(missing.querySelector('[data-testid="retry"]')).toBeNull();
    TestBed.resetTestingModule();
    const failed = create(throwError(() => new AccountingApiError('Falló', 500))).el;
    expect(failed.querySelector('[data-testid="retry"]')).not.toBeNull();
  });
});
