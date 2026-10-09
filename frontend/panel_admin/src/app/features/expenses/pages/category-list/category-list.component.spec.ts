import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { provideRouter } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';
import { CategoryDialogComponent } from '../../components/category-dialog/category-dialog.component';
import { ExpensesApiError } from '../../models/api-error';
import { ExpenseCategory } from '../../models/category';
import { CategoriesApiService } from '../../services/categories-api.service';
import { categoryPage, makeCategory } from '../../testing/expense-fixtures';
import { CategoryListComponent } from './category-list.component';

interface Hooks {
  confirmToggle(category: ExpenseCategory): Promise<boolean>;
}

describe('CategoryListComponent', () => {
  let fixture: ComponentFixture<CategoryListComponent>;
  let component: CategoryListComponent;
  let api: jasmine.SpyObj<CategoriesApiService>;
  let modal: jasmine.SpyObj<NgbModal>;
  let toastr: jasmine.SpyObj<ToastrService>;

  const active = makeCategory({ id: 'a', name: 'Materia prima' });
  const inactive = makeCategory({ id: 'b', name: 'Vieja', active: false });

  beforeEach(async () => {
    api = jasmine.createSpyObj<CategoriesApiService>('CategoriesApiService', ['list', 'activate', 'deactivate']);
    api.list.and.returnValue(of(categoryPage([active, inactive])));
    modal = jasmine.createSpyObj<NgbModal>('NgbModal', ['open']);
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    await TestBed.configureTestingModule({
      imports: [CategoryListComponent],
      providers: [
        provideRouter([]),
        { provide: CategoriesApiService, useValue: api },
        { provide: NgbModal, useValue: modal },
        { provide: ToastrService, useValue: toastr },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(CategoryListComponent);
    component = fixture.componentInstance;
  });

  const text = () => (fixture.nativeElement as HTMLElement).textContent ?? '';

  function render(): void {
    fixture.detectChanges();
    fixture.detectChanges();
  }

  it('loads only active categories by default (AC-24)', () => {
    render();
    expect(api.list).toHaveBeenCalledOnceWith({ active: true, page: 1, pageSize: 10 });
    const options = fixture.debugElement
      .queryAll(By.css('select option'))
      .map((o) => (o.nativeElement as HTMLElement).textContent?.trim());
    expect(options).toEqual(['Activas', 'Inactivas', 'Todas']);
  });

  it('lists name and state, and has no delete action (AC-24)', () => {
    render();
    expect(text()).toContain('Materia prima');
    expect(text()).toContain('Activa');
    expect(text()).toContain('Inactiva');
    const labels = fixture.debugElement.queryAll(By.css('[aria-label]')).map((e) => (e.nativeElement as HTMLElement).getAttribute('aria-label'));
    expect(labels.some((label) => /elimin|borrar/i.test(label ?? ''))).toBeFalse();
  });

  it('asks for the inactive or all categories when the filter changes (AC-24)', () => {
    render();
    component.statusControl.setValue('inactive');
    expect(api.list.calls.mostRecent().args[0]).toEqual(jasmine.objectContaining({ active: false, page: 1 }));
    component.statusControl.setValue('all');
    expect(api.list.calls.mostRecent().args[0]?.active).toBeUndefined();
  });

  it('opens the dialog to create and reloads once it is saved (AC-24)', async () => {
    const dialog = jasmine.createSpyObj<CategoryDialogComponent>('CategoryDialogComponent', ['edit']);
    modal.open.and.returnValue({ componentInstance: dialog, result: Promise.resolve(active) } as ReturnType<NgbModal['open']>);
    render();
    api.list.calls.reset();
    component.openDialog();
    await Promise.resolve();
    expect(modal.open).toHaveBeenCalledWith(CategoryDialogComponent, jasmine.anything());
    expect(dialog.edit).not.toHaveBeenCalled();
    expect(api.list).toHaveBeenCalledTimes(1);
  });

  it('opens the dialog with the category to edit and does not reload when cancelled (AC-24)', async () => {
    const dialog = jasmine.createSpyObj<CategoryDialogComponent>('CategoryDialogComponent', ['edit']);
    modal.open.and.returnValue({ componentInstance: dialog, result: Promise.reject('cancel') } as ReturnType<NgbModal['open']>);
    render();
    api.list.calls.reset();
    component.openDialog(active);
    await Promise.resolve();
    await Promise.resolve();
    expect(dialog.edit).toHaveBeenCalledWith(active);
    expect(api.list).not.toHaveBeenCalled();
  });

  it('deactivates after confirming and reloads (AC-24)', async () => {
    api.deactivate.and.returnValue(of({ ...active, active: false }));
    spyOn(component as unknown as Hooks, 'confirmToggle').and.resolveTo(true);
    render();
    api.list.calls.reset();
    await component.toggleActive(active);
    expect(api.deactivate).toHaveBeenCalledWith('a');
    expect(toastr.success).toHaveBeenCalledWith('Categoría desactivada');
    expect(api.list).toHaveBeenCalledTimes(1);
  });

  it('activates an inactive category after confirming (AC-24)', async () => {
    api.activate.and.returnValue(of({ ...inactive, active: true }));
    spyOn(component as unknown as Hooks, 'confirmToggle').and.resolveTo(true);
    render();
    await component.toggleActive(inactive);
    expect(api.activate).toHaveBeenCalledWith('b');
    expect(toastr.success).toHaveBeenCalledWith('Categoría activada');
  });

  it('does nothing when the confirmation is cancelled and reports failures', async () => {
    const confirm = spyOn(component as unknown as Hooks, 'confirmToggle').and.resolveTo(false);
    render();
    await component.toggleActive(active);
    expect(api.deactivate).not.toHaveBeenCalled();

    confirm.and.resolveTo(true);
    api.deactivate.and.returnValue(throwError(() => new ExpensesApiError('Categoría no encontrada.', 404)));
    await component.toggleActive(active);
    expect(toastr.error).toHaveBeenCalledWith('Categoría no encontrada.');
  });
});
