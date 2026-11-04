import { tr } from '../../../../core/i18n/translate';
import { TranslatePipe } from '@ngx-translate/core';
import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { NgbAccordionModule, NgbCollapseModule } from '@ng-bootstrap/ng-bootstrap';
import { LanguageSelectorComponent } from '../../../../shared/components/language-selector/language-selector.component';
import { AuthService } from '../../../../core/service/auth.service';
import { APP_PATHS } from '../../../../core/routing/app-paths';
import {
  BENEFITS,
  CHANNEL_NOTE,
  DELIVERED_ROWS,
  FAQ,
  FLOW_STEPS,
  FREE_LIMITS_NOTE,
  FREE_PLAN_FEATURES,
  FREE_PLAN_LIMIT_TEXT,
  GET_STARTED,
  NAV_ANCHORS,
  PERIODS,
  PRO_PAYMENT_LABEL,
  PRO_PLAN_FEATURE,
  PROFIT_NOTE,
  READY_ROWS,
  RECOGNITION,
} from '../../models/landing-content';

export type BillingPeriod = 'monthly' | 'annual';

@Component({
  selector: 'app-landing',
  templateUrl: './landing.component.html',
  styleUrls: [
    './landing-header.scss',
    './landing-sections.scss',
    './landing-plans.scss',
  ],
  imports: [TranslatePipe, LanguageSelectorComponent, RouterLink, NgbAccordionModule, NgbCollapseModule],
})
export class LandingComponent {
  private authService = inject(AuthService);

  readonly paths = APP_PATHS;
  readonly anchors = NAV_ANCHORS;
  get freeLimitsNote(): string {
    return FREE_LIMITS_NOTE();
  }
  get recognition(): readonly string[] {
    return RECOGNITION();
  }
  readonly benefits = BENEFITS;
  get channelNote(): string {
    return CHANNEL_NOTE();
  }
  readonly flowSteps = FLOW_STEPS;
  readonly readyRows = READY_ROWS;
  readonly deliveredRows = DELIVERED_ROWS;
  get periods(): readonly string[] {
    return PERIODS();
  }
  get selectedPeriod(): string {
    return tr('EXPENSES.EXPENSE_LIST.ESTE_MES');
  }
  get profitNote(): string {
    return PROFIT_NOTE();
  }
  readonly getStarted = GET_STARTED;
  get freeFeatures(): readonly string[] {
    return FREE_PLAN_FEATURES();
  }
  get freeLimitText(): string {
    return FREE_PLAN_LIMIT_TEXT();
  }
  get proFeature(): string {
    return PRO_PLAN_FEATURE();
  }
  get proPaymentLabel(): string {
    return PRO_PAYMENT_LABEL();
  }
  readonly faq = FAQ;

  readonly period = signal<BillingPeriod>('annual');
  readonly menuCollapsed = signal(true);

  /** La sesión es del servicio de autenticación; la landing solo adapta el CTA. */
  readonly isAuthenticated = computed(() => this.authService.isAuthenticated);

  primaryCtaLabel(): string {
    return this.isAuthenticated() ? tr('LANDING.LANDING.IR_A_MI_PANEL') : tr('LANDING.LANDING.EMPEZAR_GRATIS');
  }
  readonly primaryCtaPath = computed(() =>
    this.isAuthenticated() ? this.paths.dashboard : this.paths.signup
  );

  setPeriod(period: BillingPeriod): void {
    this.period.set(period);
  }

  toggleMenu(): void {
    this.menuCollapsed.update((collapsed) => !collapsed);
  }

  scrollTo(id: string, event: Event): void {
    event.preventDefault();
    this.menuCollapsed.set(true);
    const target = document.getElementById(id);
    if (!target) {
      return;
    }
    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
    target.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
  }
}
