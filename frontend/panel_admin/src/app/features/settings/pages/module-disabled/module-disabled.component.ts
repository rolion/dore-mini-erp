import { AsyncPipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { Observable, combineLatest, map } from 'rxjs';
import { ModulesService } from '../../../../core/service/modules.service';

/** Destino cuando se abre un módulo deshabilitado (URL guardada) o la API lo rechaza con `module_disabled`. */
export const HOME_WITH_REPORTING = '/dashboard/main';
export const HOME_BASE = '/catalog/products';

@Component({
  selector: 'app-module-disabled',
  imports: [AsyncPipe, RouterLink],
  template: `
    <section class="main-content">
      <ul class="breadcrumb breadcrumb-style ">
        <li class="breadcrumb-item">
          <h5 class="page-title m-b-0">Módulo no habilitado</h5>
        </li>
        <li class="breadcrumb-item bcrumb-1">
          <a [routerLink]="home$ | async" aria-label="Inicio"><i class="fas fa-home font-17"></i></a>
        </li>
        <li class="breadcrumb-item">Módulo no habilitado</li>
      </ul>
      <div class="section-body">
        <div class="card">
          <div class="card-header">
            <h2><strong>Módulo no habilitado</strong></h2>
          </div>
          <div class="card-body">
            <p>
              @if (moduleName$ | async; as name) {
                El módulo {{ name }} no está habilitado para tu empresa.
              } @else {
                Este módulo no está habilitado para tu empresa.
              }
              Un administrador puede habilitarlo en Configuración › Módulos.
            </p>
            <a [routerLink]="home$ | async" class="btn btn-primary">Volver al inicio</a>
          </div>
        </div>
      </div>
    </section>
  `,
})
export class ModuleDisabledComponent {
  private modules = inject(ModulesService);
  private route = inject(ActivatedRoute);

  /** Reportes habilitado → panel inicial; si no, Catálogo, que es base y siempre está disponible. */
  readonly home$: Observable<string> = this.modules.enabledKeys$.pipe(
    map((keys) => (keys?.has('reporting') ? HOME_WITH_REPORTING : HOME_BASE))
  );

  readonly moduleName$: Observable<string | null> = combineLatest([this.route.queryParamMap, this.modules.modules$]).pipe(
    map(([params, modules]) => modules?.find((m) => m.key === params.get('module'))?.name ?? null)
  );
}
