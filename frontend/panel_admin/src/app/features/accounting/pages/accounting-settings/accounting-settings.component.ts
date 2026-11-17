import { Component, inject } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { AccountClassesTabComponent } from '../../components/account-classes-tab/account-classes-tab.component';
import { PeriodsTabComponent } from '../../components/periods-tab/periods-tab.component';

export type SettingsTab = 'classes' | 'periods';

const LEGACY_TABS: readonly string[] = ['methods', 'classifications', 'expenses', 'cutoff'];

/** Contabilidad › Configuración: Clasificaciones contables y Períodos fiscales; el resto enlaza a la pantalla heredada. */
@Component({
  selector: 'app-accounting-settings',
  templateUrl: './accounting-settings.component.html',
  imports: [TranslatePipe, RouterLink, AccountClassesTabComponent, PeriodsTabComponent],
})
export class AccountingSettingsComponent {
  readonly tabs: readonly SettingsTab[] = ['classes', 'periods'];
  /** Pestaña inicial: `?tab=periods` abre «Períodos fiscales». */
  tab: SettingsTab = this.initialTab();

  private initialTab(): SettingsTab {
    const requested = inject(ActivatedRoute).snapshot.queryParamMap.get('tab');
    this.redirectOldTab(requested, inject(Router));
    return this.tabs.find((tab) => tab === requested) ?? 'classes';
  }

  /** Marcadores antiguos: las pestañas que ya no están aquí llevan a su nueva pantalla (REV-03). */
  private redirectOldTab(requested: string | null, router: Router): void {
    if (requested === 'accounts') {
      void router.navigate(['/pocketbiz/accounting/accounts'], { replaceUrl: true });
    } else if (requested && LEGACY_TABS.includes(requested)) {
      void router.navigate(['/pocketbiz/accounting/settings/legacy'], { queryParams: { tab: requested }, replaceUrl: true });
    }
  }

  select(tab: SettingsTab): void {
    this.tab = tab;
  }

  /** Patrón WAI-ARIA de pestañas: flechas, Inicio y Fin mueven la selección y el foco. */
  onTabKeydown(event: KeyboardEvent): void {
    const last = this.tabs.length - 1;
    const current = this.tabs.indexOf(this.tab);
    const target: Record<string, number> = {
      ArrowRight: current === last ? 0 : current + 1,
      ArrowLeft: current === 0 ? last : current - 1,
      Home: 0,
      End: last,
    };
    const index = target[event.key];
    if (index === undefined) {
      return;
    }
    event.preventDefault();
    this.select(this.tabs[index]);
    const list = (event.currentTarget as HTMLElement).closest('[role="tablist"]');
    list?.querySelector<HTMLElement>(`#tab-${this.tabs[index]}`)?.focus();
  }
}
