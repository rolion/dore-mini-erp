import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';
import { ExpensesApiError } from '../../models/api-error';
import { CategoriesApiService } from '../../services/categories-api.service';
import { makeCategory } from '../../testing/expense-fixtures';
import { CategoryDialogComponent } from './category-dialog.component';

describe('CategoryDialogComponent', () => {
  let fixture: ComponentFixture<CategoryDialogComponent>;
  let component: CategoryDialogComponent;
  let api: jasmine.SpyObj<CategoriesApiService>;
  let activeModal: jasmine.SpyObj<NgbActiveModal>;
  let toastr: jasmine.SpyObj<ToastrService>;

  beforeEach(async () => {
    api = jasmine.createSpyObj<CategoriesApiService>('CategoriesApiService', ['create', 'rename']);
    activeModal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    await TestBed.configureTestingModule({
      imports: [CategoryDialogComponent],
      providers: [
        { provide: CategoriesApiService, useValue: api },
        { provide: NgbActiveModal, useValue: activeModal },
        { provide: ToastrService, useValue: toastr },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(CategoryDialogComponent);
    component = fixture.componentInstance;
  });

  const text = () => (fixture.nativeElement as HTMLElement).textContent ?? '';

  it('requires a name before saving (AC-01)', () => {
    fixture.detectChanges();
    expect(text()).toContain('Nueva categoría');
    component.form.controls.name.setValue('   ');
    component.onSubmit();
    fixture.detectChanges();
    expect(api.create).not.toHaveBeenCalled();
    expect(text()).toContain('El nombre es obligatorio.');
  });

  it('creates a category with the trimmed name and closes with it (AC-01)', () => {
    const saved = makeCategory({ name: 'Empaque' });
    api.create.and.returnValue(of(saved));
    fixture.detectChanges();
    component.form.controls.name.setValue('  Empaque ');
    component.onSubmit();
    expect(api.create).toHaveBeenCalledWith('Empaque');
    expect(toastr.success).toHaveBeenCalledWith('Categoría creada');
    expect(activeModal.close).toHaveBeenCalledWith(saved);
  });

  it('renames when editing, starting from the current name (AC-02)', () => {
    const category = makeCategory({ id: 'c9', name: 'Empaque' });
    api.rename.and.returnValue(of({ ...category, name: 'Embalaje' }));
    component.edit(category);
    fixture.detectChanges();
    expect(text()).toContain('Editar categoría');
    expect(component.form.controls.name.value).toBe('Empaque');
    component.form.controls.name.setValue('Embalaje');
    component.onSubmit();
    expect(api.rename).toHaveBeenCalledWith('c9', 'Embalaje');
    expect(toastr.success).toHaveBeenCalledWith('Categoría actualizada');
    expect(activeModal.close).toHaveBeenCalled();
  });

  it('keeps the dialog open and shows the duplicate-name error under the field (AC-01)', () => {
    api.create.and.returnValue(
      throwError(() => new ExpensesApiError('Revisa los datos ingresados.', 400, { name: ['Ya existe una categoría con ese nombre.'] })),
    );
    fixture.detectChanges();
    component.form.controls.name.setValue('Empaque');
    component.onSubmit();
    fixture.detectChanges();
    expect(activeModal.close).not.toHaveBeenCalled();
    expect(text()).toContain('Ya existe una categoría con ese nombre.');
    expect(component.saving).toBeFalse();
    component.form.controls.name.setValue('Otra');
    expect(component.serverError).toBe('');
  });

  it('shows a toast for failures without a field error', () => {
    api.create.and.returnValue(throwError(() => new ExpensesApiError('No se pudo conectar con el servidor.', 0)));
    fixture.detectChanges();
    component.form.controls.name.setValue('Empaque');
    component.onSubmit();
    expect(toastr.error).toHaveBeenCalledWith('No se pudo conectar con el servidor.');
  });
});
