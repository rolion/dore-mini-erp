import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { of } from 'rxjs';
import { UnitsApiService } from '../../services/units-api.service';
import { makeUnit } from '../../testing/inventory-fixtures';
import { UnitsTabComponent } from './units-tab.component';

describe('UnitsTabComponent', () => {
  let fixture: ComponentFixture<UnitsTabComponent>;
  let component: UnitsTabComponent;
  let api: jasmine.SpyObj<UnitsApiService>;
  let toastr: jasmine.SpyObj<ToastrService>;

  beforeEach(async () => {
    api = jasmine.createSpyObj<UnitsApiService>('UnitsApiService', ['list', 'activate', 'deactivate']);
    api.list.and.returnValue(of({ count: 1, next: null, previous: null, results: [makeUnit()] }));
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    await TestBed.configureTestingModule({
      imports: [UnitsTabComponent],
      providers: [
        { provide: UnitsApiService, useValue: api },
        { provide: ToastrService, useValue: toastr },
        { provide: NgbModal, useValue: jasmine.createSpyObj<NgbModal>('NgbModal', ['open']) },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(UnitsTabComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  const el = () => fixture.nativeElement as HTMLElement;

  it('lists active units with abbreviation and fractions (AC-07)', () => {
    expect(api.list.calls.mostRecent().args[0]?.active).toBeTrue();
    const row = el().querySelector('tbody tr')?.textContent ?? '';
    expect(row).toContain('Kilogramo');
    expect(row).toContain('kg');
    expect(row).toContain('Sí');
  });

  it('shows the empty state while the company has no units (AC-07)', () => {
    api.list.and.returnValue(of({ count: 0, next: null, previous: null, results: [] }));
    component.reload();
    fixture.detectChanges();
    expect(el().textContent).toContain('Sin unidades. Crea la primera con +.');
  });

  it('filters by status and offers no delete action (AC-07)', () => {
    component.statusControl.setValue('all');
    expect(api.list.calls.mostRecent().args[0]?.active).toBeUndefined();
    component.statusControl.setValue('inactive');
    expect(api.list.calls.mostRecent().args[0]?.active).toBeFalse();
    expect(el().querySelector('[aria-label="Eliminar"]')).toBeNull();
  });

  it('deactivates a unit and reloads (AC-07)', () => {
    api.deactivate.and.returnValue(of(makeUnit({ active: false })));
    component.toggleActive(makeUnit());
    expect(api.deactivate).toHaveBeenCalledWith('u-1');
    expect(toastr.success).toHaveBeenCalledWith('Unidad desactivada');
  });
});
