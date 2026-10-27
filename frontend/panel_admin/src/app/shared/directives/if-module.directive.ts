import { Directive, EmbeddedViewRef, TemplateRef, ViewContainerRef, effect, inject, input } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ModulesService } from '../../core/service/modules.service';

/**
 * Muestra su contenido solo cuando el módulo indicado está habilitado para la empresa (p. ej.
 * `<div *appIfModule="'inventory'">…</div>`). No renderiza mientras no se conocen los módulos y reacciona si
 * cambian. Es una comodidad de interfaz: la API rechaza igualmente lo que no corresponda.
 */
@Directive({
  selector: '[appIfModule]',
})
export class IfModuleDirective {
  readonly appIfModule = input.required<string>();

  private template = inject<TemplateRef<unknown>>(TemplateRef);
  private container = inject(ViewContainerRef);
  private enabled = toSignal(inject(ModulesService).enabledKeys$, { initialValue: null });
  private view: EmbeddedViewRef<unknown> | null = null;

  constructor() {
    effect(() => {
      const keys = this.enabled();
      const show = keys !== null && keys.has(this.appIfModule());
      if (show && !this.view) {
        this.view = this.container.createEmbeddedView(this.template);
      } else if (!show && this.view) {
        this.container.clear();
        this.view = null;
      }
    });
  }
}
