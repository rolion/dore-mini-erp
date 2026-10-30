import { AsyncPipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ModulesService } from '../../../../core/service/modules.service';
import { UnitsTabComponent } from '../../components/units-tab/units-tab.component';
import { WarehousesTabComponent } from '../../components/warehouses-tab/warehouses-tab.component';

export type ConfigurationTab = 'warehouses' | 'units';

/** Inventario › Almacenes y unidades: dos pestañas, cada una con listado y formulario de alta/edición. */
@Component({
  selector: 'app-inventory-configuration',
  templateUrl: './inventory-configuration.component.html',
  imports: [RouterLink, AsyncPipe, WarehousesTabComponent, UnitsTabComponent],
})
export class InventoryConfigurationComponent {
  /** Módulos habilitados: «Valoración» solo se ofrece con Costeo (la API es la barrera real). */
  readonly enabledKeys$ = inject(ModulesService).enabledKeys$;
  tab: ConfigurationTab = 'warehouses';

  select(tab: ConfigurationTab): void {
    this.tab = tab;
  }
}
