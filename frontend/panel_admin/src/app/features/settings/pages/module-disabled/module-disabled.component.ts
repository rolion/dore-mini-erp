import { TranslatePipe } from '@ngx-translate/core';
import { AsyncPipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { Observable, combineLatest, map } from 'rxjs';
import { APP_PATHS } from '../../../../core/routing/app-paths';
import { ModulesService } from '../../../../core/service/modules.service';

/** Destino cuando se abre un módulo deshabilitado (URL guardada) o la API lo rechaza con `module_disabled`. */
export const HOME_WITH_REPORTING = APP_PATHS.dashboard;
export const HOME_BASE = APP_PATHS.catalog;

@Component({
  selector: 'app-module-disabled',
  imports: [TranslatePipe, AsyncPipe, RouterLink],
  template: `
    <section class="main-content">
      <ul class="breadcrumb breadcrumb-style ">
        <li class="breadcrumb-item">
          <h5 class="page-title m-b-0">{{ 'SETTINGS.MODULE_DISABLED.MODULE_NOT_ENABLED' | translate }}</h5>
        </li>
        <li class="breadcrumb-item bcrumb-1">
          <a [routerLink]="home$ | async" [attr.aria-label]="'COMMON.INICIO' | translate"><i class="fas fa-home font-17"></i></a>
        </li>
        <li class="breadcrumb-item">{{ 'SETTINGS.MODULE_DISABLED.MODULE_NOT_ENABLED' | translate }}</li>
      </ul>
      <div class="section-body">
        <div class="card">
          <div class="card-header">
            <h2><strong>{{ 'SETTINGS.MODULE_DISABLED.MODULE_NOT_ENABLED' | translate }}</strong></h2>
          </div>
          <div class="card-body">
            <p>
              @if (moduleName$ | async; as name) {
                {{ 'SETTINGS.MODULE_DISABLED.NAMED_NOT_ENABLED' | translate: { p0: name } }}
              } @else {
                {{ 'SETTINGS.MODULE_DISABLED.THIS_NOT_ENABLED' | translate }}
              }
              {{ 'SETTINGS.MODULE_DISABLED.ADMIN_CAN_ENABLE' | translate }}
            </p>
            <a [routerLink]="home$ | async" class="btn btn-primary">{{ 'COMMON.BACK_TO_HOME' | translate }}</a>
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
