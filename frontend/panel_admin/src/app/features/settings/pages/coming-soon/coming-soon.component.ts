import { Component, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

/** Pantalla provisional de módulos habilitables que aún no existen (Compras, Inventario). */
@Component({
  selector: 'app-coming-soon',
  imports: [RouterLink],
  template: `
    <section class="main-content">
      <ul class="breadcrumb breadcrumb-style ">
        <li class="breadcrumb-item">
          <h5 class="page-title m-b-0">{{ title }}</h5>
        </li>
        <li class="breadcrumb-item bcrumb-1">
          <a routerLink="/dashboard/main"><i class="fas fa-home font-17"></i></a>
        </li>
        <li class="breadcrumb-item">{{ title }}</li>
      </ul>
      <div class="section-body">
        <div class="card">
          <div class="card-header">
            <h4>{{ title }}</h4>
          </div>
          <div class="card-body">
            <p>Próximamente. Este módulo aún no está disponible, pero ya está habilitado para tu empresa.</p>
            <a routerLink="/dashboard/main" class="btn btn-light">Volver al panel</a>
          </div>
        </div>
      </div>
    </section>
  `,
})
export class ComingSoonComponent {
  readonly title = (inject(ActivatedRoute).snapshot.data['title'] as string | undefined) ?? 'Módulo';
}
