import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { CrmApiError } from '../../models/board';
import { CrmActivitiesApiService } from '../../services/crm-activities-api.service';
import { makeActivity } from '../../testing/crm-fixtures';
import { ActivityDialogComponent } from './activity-dialog.component';

describe('ActivityDialogComponent', () => {
  let fixture: ComponentFixture<ActivityDialogComponent>;
  let component: ActivityDialogComponent;
  let api: jasmine.SpyObj<CrmActivitiesApiService>;
  let modal: jasmine.SpyObj<NgbActiveModal>;
  const related = { type: 'customer' as const, id: 'c-1', name: 'Ana Pérez' };

  function setup(history = [makeActivity()]): void {
    api = jasmine.createSpyObj<CrmActivitiesApiService>('CrmActivitiesApiService', ['list', 'create']);
    api.list.and.returnValue(of({ count: history.length, results: history }));
    modal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    TestBed.configureTestingModule({
      imports: [ActivityDialogComponent],
      providers: [...provideTestTranslations(), { provide: CrmActivitiesApiService, useValue: api }, { provide: NgbActiveModal, useValue: modal }],
    });
    fixture = TestBed.createComponent(ActivityDialogComponent);
    component = fixture.componentInstance;
    component.open(related);
    fixture.detectChanges();
  }

  const text = (): string => (fixture.nativeElement as HTMLElement).textContent ?? '';

  it('shows the related name and its history, most recent first (AC-07, AC-10)', () => {
    setup([makeActivity({ notes: 'Nueva nota' }), makeActivity({ id: 'a-2', notes: 'Vieja' })]);
    expect(api.list).toHaveBeenCalledWith(related);
    expect(text()).toContain('Ana Pérez');
    expect(fixture.nativeElement.querySelectorAll('[data-testid="history-item"]').length).toBe(2);
  });

  it('shows the empty history message', () => {
    setup([]);
    expect(fixture.nativeElement.querySelector('[data-testid="history-empty"]')).not.toBeNull();
  });

  it('cannot save without outcome or notes; then creates and closes with the activity (AC-07)', () => {
    setup();
    expect(component.canSave).toBeFalse();
    component.form.patchValue({ channel: 'whatsapp', outcome: 'interested' });
    expect(component.canSave).toBeTrue();
    const saved = makeActivity({ channel: 'whatsapp' });
    api.create.and.returnValue(of(saved));
    component.save();
    expect(api.create).toHaveBeenCalledWith({ related, channel: 'whatsapp', outcome: 'interested', notes: '' });
    expect(modal.close).toHaveBeenCalledWith(saved);
  });

  it('shows server field errors without closing', () => {
    setup();
    component.form.patchValue({ notes: 'x' });
    api.create.and.returnValue(throwError(() => new CrmApiError('Datos inválidos', 400, { occurredAt: 'La fecha no puede estar en el futuro.' })));
    component.save();
    fixture.detectChanges();
    expect(modal.close).not.toHaveBeenCalled();
    expect(text()).toContain('La fecha no puede estar en el futuro.');
  });
});
