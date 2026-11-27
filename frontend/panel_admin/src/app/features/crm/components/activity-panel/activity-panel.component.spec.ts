import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { CrmApiError } from '../../models/board';
import { CrmActivitiesApiService } from '../../services/crm-activities-api.service';
import { makeActivity } from '../../testing/crm-fixtures';
import { ActivityPanelComponent } from './activity-panel.component';

describe('ActivityPanelComponent', () => {
  let fixture: ComponentFixture<ActivityPanelComponent>;
  let component: ActivityPanelComponent;
  let api: jasmine.SpyObj<CrmActivitiesApiService>;
  const related = { type: 'opportunity' as const, id: 'o-1', name: 'Llamar' };

  function setup(history = [makeActivity({ channel: 'call', outcome: 'interested', notes: 'Quiere precio' })]): void {
    api = jasmine.createSpyObj<CrmActivitiesApiService>('CrmActivitiesApiService', ['list', 'create']);
    api.list.and.returnValue(of({ count: history.length, results: history }));
    TestBed.configureTestingModule({
      imports: [ActivityPanelComponent],
      providers: [...provideTestTranslations(), { provide: CrmActivitiesApiService, useValue: api }],
    });
    fixture = TestBed.createComponent(ActivityPanelComponent);
    fixture.componentRef.setInput('related', related);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  const el = (): HTMLElement => fixture.nativeElement as HTMLElement;
  const q = (id: string): HTMLElement | null => el().querySelector(`[data-testid="${id}"]`);

  it('lists the activities as channel tag, outcome tag, date and note', () => {
    setup();
    expect(api.list).toHaveBeenCalledWith(related, 1);
    expect(q('channel-badge')).not.toBeNull();
    expect(q('outcome-badge')).not.toBeNull();
    expect(q('history-item')?.textContent).toContain('Quiere precio');
  });

  it('opens the form on the column top with Add activity, and hides it again', () => {
    setup();
    expect(q('activity-form')).toBeNull();
    (q('add-activity') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(q('activity-form')).not.toBeNull();
    expect(q('activity-date')).not.toBeNull();
    (q('add-activity') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(q('activity-form')).toBeNull();
  });

  it('saves a valid activity, closes the form and reloads the list', () => {
    setup();
    api.create.and.returnValue(of(makeActivity()));
    component.toggleForm();
    component.form.patchValue({ channel: 'whatsapp', notes: 'Hola' });
    component.save();
    expect(api.create.calls.mostRecent().args[0].related).toEqual(related);
    expect(component.formOpen).toBeFalse();
    expect(api.list).toHaveBeenCalledTimes(2);
  });

  it('does not save without outcome or note', () => {
    setup();
    component.save();
    expect(api.create).not.toHaveBeenCalled();
  });

  it('keeps the form open and shows the server error', () => {
    setup();
    api.create.and.returnValue(throwError(() => new CrmApiError('Falló', 500)));
    component.toggleForm();
    component.form.patchValue({ notes: 'Hola' });
    component.save();
    fixture.detectChanges();
    expect(component.formOpen).toBeTrue();
    expect(q('activity-error')?.textContent).toContain('Falló');
  });
});
