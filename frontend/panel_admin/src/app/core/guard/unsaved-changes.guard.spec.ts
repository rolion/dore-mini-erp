import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { UNSAVED_CHANGES_MESSAGE, unsavedChangesGuard } from './unsaved-changes.guard';

describe('unsavedChangesGuard', () => {
  const run = (dirty: boolean) =>
    TestBed.runInInjectionContext(() =>
      unsavedChangesGuard(
        { hasUnsavedChanges: () => dirty },
        {} as ActivatedRouteSnapshot,
        {} as RouterStateSnapshot,
        {} as RouterStateSnapshot,
      ),
    );

  it('lets the user leave without asking when nothing changed (UI-05)', () => {
    const confirm = spyOn(window, 'confirm');
    expect(run(false)).toBeTrue();
    expect(confirm).not.toHaveBeenCalled();
  });

  it('asks for confirmation with unsaved changes and follows the answer (UI-05)', () => {
    const confirm = spyOn(window, 'confirm').and.returnValues(false, true);
    expect(run(true)).toBeFalse();
    expect(run(true)).toBeTrue();
    expect(confirm).toHaveBeenCalledWith(UNSAVED_CHANGES_MESSAGE);
  });
});
