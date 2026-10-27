import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { of } from 'rxjs';
import { UnitsApiService } from '../../services/units-api.service';
import { WarehousesApiService } from '../../services/warehouses-api.service';
import { InventoryConfigurationComponent } from './inventory-configuration.component';

describe('InventoryConfigurationComponent', () => {
  function create() {
    const empty = { count: 0, next: null, previous: null, results: [] };
    const warehouses = jasmine.createSpyObj<WarehousesApiService>('WarehousesApiService', ['list']);
    const units = jasmine.createSpyObj<UnitsApiService>('UnitsApiService', ['list']);
    warehouses.list.and.returnValue(of(empty));
    units.list.and.returnValue(of(empty));
    TestBed.configureTestingModule({
      imports: [InventoryConfigurationComponent],
      providers: [
        provideRouter([]),
        { provide: WarehousesApiService, useValue: warehouses },
        { provide: UnitsApiService, useValue: units },
        { provide: ToastrService, useValue: jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']) },
      ],
    });
    const fixture = TestBed.createComponent(InventoryConfigurationComponent);
    fixture.detectChanges();
    return { fixture, warehouses, units, el: fixture.nativeElement as HTMLElement };
  }

  it('opens on «Almacenes» and switches to «Unidades» (UI-03)', () => {
    const { fixture, warehouses, units, el } = create();
    const tabs = Array.from(el.querySelectorAll('[role="tab"]'));
    expect(tabs.map((t) => t.textContent?.trim())).toEqual(['Almacenes', 'Unidades']);
    expect(tabs[0].getAttribute('aria-selected')).toBe('true');
    expect(warehouses.list).toHaveBeenCalled();
    expect(units.list).not.toHaveBeenCalled();

    (tabs[1] as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(units.list).toHaveBeenCalled();
    expect(el.querySelector('#panel-units')).not.toBeNull();
    expect(el.querySelector('#panel-warehouses')).toBeNull();
  });
});
