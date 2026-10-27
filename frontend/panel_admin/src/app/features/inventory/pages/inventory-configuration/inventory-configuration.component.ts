import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { UnitsTabComponent } from '../../components/units-tab/units-tab.component';
import { WarehousesTabComponent } from '../../components/warehouses-tab/warehouses-tab.component';

export type ConfigurationTab = 'warehouses' | 'units';

/** Inventario › Almacenes y unidades: dos pestañas, cada una con listado y formulario de alta/edición. */
@Component({
  selector: 'app-inventory-configuration',
  templateUrl: './inventory-configuration.component.html',
  imports: [RouterLink, WarehousesTabComponent, UnitsTabComponent],
})
export class InventoryConfigurationComponent {
  tab: ConfigurationTab = 'warehouses';

  select(tab: ConfigurationTab): void {
    this.tab = tab;
  }
}
