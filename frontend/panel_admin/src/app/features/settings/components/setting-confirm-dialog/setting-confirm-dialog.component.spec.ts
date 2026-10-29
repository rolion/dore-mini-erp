import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { SettingConfirmDialogComponent } from './setting-confirm-dialog.component';

describe('SettingConfirmDialogComponent', () => {
  let fixture: ComponentFixture<SettingConfirmDialogComponent>;
  let active: jasmine.SpyObj<NgbActiveModal>;
  const click = (testId: string) =>
    ((fixture.nativeElement as HTMLElement).querySelector(`[data-testid="${testId}"]`) as HTMLButtonElement).click();

  beforeEach(() => {
    active = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    TestBed.configureTestingModule({
      imports: [SettingConfirmDialogComponent],
      providers: [{ provide: NgbActiveModal, useValue: active }],
    });
    fixture = TestBed.createComponent(SettingConfirmDialogComponent);
    Object.assign(fixture.componentInstance, { title: 'Permitir stock negativo', message: 'Podrán existir saldos negativos.', confirmLabel: 'Permitir' });
    fixture.detectChanges();
  });

  it('shows the explanation and closes on accept (AC-05)', () => {
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Podrán existir saldos negativos.');
    click('confirm-accept');
    expect(active.close).toHaveBeenCalledWith(true);
  });

  it('dismisses on cancel', () => {
    const cancel = Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('button')).find((b) => b.textContent?.trim() === 'Cancelar');
    cancel?.click();
    expect(active.dismiss).toHaveBeenCalled();
  });
});
