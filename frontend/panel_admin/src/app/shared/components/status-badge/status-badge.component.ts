import { Component, computed, input } from '@angular/core';

export type StatusTone = 'success' | 'warning' | 'danger' | 'info' | 'muted';

const ICONS: Record<StatusTone, string> = {
  success: 'fa-check-circle',
  warning: 'fa-clock',
  danger: 'fa-times-circle',
  info: 'fa-adjust',
  muted: 'fa-minus-circle',
};

/** Clases de Bootstrap 5.3 para cada tono: fondo tenue + texto de énfasis (pares con contraste AA). */
const TONE_CLASSES: Record<StatusTone, string> = {
  success: 'bg-success-subtle text-success-emphasis border-success-subtle',
  warning: 'bg-warning-subtle text-warning-emphasis border-warning-subtle',
  danger: 'bg-danger-subtle text-danger-emphasis border-danger-subtle',
  info: 'bg-info-subtle text-info-emphasis border-info-subtle',
  muted: 'bg-secondary-subtle text-secondary-emphasis border-secondary-subtle',
};

/** Estado con icono + fondo tintado + texto: el color nunca va solo y el contraste cumple AA. */
@Component({
  selector: 'app-status-badge',
  template: `<span class="badge border d-inline-flex align-items-center gap-1 fw-semibold" [class]="toneClasses()">
    <i class="fas" [class]="icon()" aria-hidden="true"></i>{{ label() }}
  </span>`,
})
export class StatusBadgeComponent {
  readonly tone = input.required<StatusTone>();
  readonly label = input.required<string>();

  readonly icon = computed(() => ICONS[this.tone()]);
  readonly toneClasses = computed(() => TONE_CLASSES[this.tone()]);
}
