import { TestBed } from '@angular/core/testing';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { AccountingApiError, AccountingSettings } from '../../models/accounting';
import { AccountingApiService } from '../../services/accounting-api.service';
import { CutoffTabComponent } from './cutoff-tab.component';

const open: AccountingSettings = { cutoffDate: '2026-11-01', enabledAt: '2026-11-01', locked: false, gaps: [] };

describe('CutoffTabComponent', () => {
  let api: jasmine.SpyObj<AccountingApiService>;

  function create(settings: AccountingSettings) {
    api = jasmine.createSpyObj<AccountingApiService>('AccountingApiService', ['getSettings', 'updateCutoff']);
    api.getSettings.and.returnValue(of(settings));
    TestBed.configureTestingModule({
      imports: [CutoffTabComponent],
      providers: [
        ...provideTestTranslations(),
        { provide: AccountingApiService, useValue: api },
        { provide: ToastrService, useValue: jasmine.createSpyObj('ToastrService', ['success', 'error']) },
      ],
    });
    const fixture = TestBed.createComponent(CutoffTabComponent);
    fixture.detectChanges();
    return fixture;
  }

  it('says accounting is not enabled when there is no cutoff (UI-04)', () => {
    const fixture = create({ cutoffDate: null, enabledAt: null, locked: false, gaps: [] });
    expect(fixture.nativeElement.textContent).toContain('Contabilidad aún no está habilitada');
  });

  it('shows the cutoff, the non-retroactive note and no gaps (UI-01)', () => {
    const fixture = create(open);
    const text = fixture.nativeElement.textContent as string;
    expect(fixture.componentInstance.cutoffControl.value).toBe('2026-11-01');
    expect(text).toContain('no se contabiliza automáticamente');
    expect(fixture.nativeElement.querySelector('[data-testid="no-gaps"]')).not.toBeNull();
  });

  it('lists the periods without coverage', () => {
    const fixture = create({ ...open, gaps: [{ from: '2026-11-03', to: '2026-11-08' }] });
    expect(fixture.nativeElement.querySelector('[data-testid="gaps"]').textContent).toContain('03/11/2026');
  });

  it('locks the date once there are movements (AC-06)', () => {
    const fixture = create({ ...open, locked: true });
    expect(fixture.componentInstance.cutoffControl.disabled).toBeTrue();
    expect(fixture.nativeElement.querySelector('[data-testid="locked"]')).not.toBeNull();
    fixture.componentInstance.save();
    expect(api.updateCutoff).not.toHaveBeenCalled();
  });

  it('saves a new cutoff while there are no movements', () => {
    const fixture = create(open);
    api.updateCutoff.and.returnValue(of({ ...open, cutoffDate: '2026-10-15' }));
    fixture.componentInstance.cutoffControl.setValue('2026-10-15');
    fixture.componentInstance.save();
    expect(api.updateCutoff).toHaveBeenCalledWith('2026-10-15');
    expect(fixture.componentInstance.settings?.cutoffDate).toBe('2026-10-15');
  });

  it('shows the server error when the cutoff is rejected', () => {
    const fixture = create(open);
    api.updateCutoff.and.returnValue(throwError(() => new AccountingApiError('No se puede cambiar la fecha de corte.', 409, {}, 'cutoff_locked')));
    fixture.componentInstance.save();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[data-testid="cutoff-error"]').textContent).toContain('No se puede cambiar');
  });
});
