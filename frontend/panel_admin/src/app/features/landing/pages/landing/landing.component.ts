import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { NgbAccordionModule, NgbCollapseModule } from '@ng-bootstrap/ng-bootstrap';
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
  styleUrls: ['./landing.component.scss'],
  imports: [RouterLink, NgbAccordionModule, NgbCollapseModule],
})
export class LandingComponent {
  private authService = inject(AuthService);

  readonly paths = APP_PATHS;
  readonly anchors = NAV_ANCHORS;
  readonly freeLimitsNote = FREE_LIMITS_NOTE;
  readonly recognition = RECOGNITION;
  readonly benefits = BENEFITS;
  readonly channelNote = CHANNEL_NOTE;
  readonly flowSteps = FLOW_STEPS;
  readonly readyRows = READY_ROWS;
  readonly deliveredRows = DELIVERED_ROWS;
  readonly periods = PERIODS;
  readonly selectedPeriod = 'Este mes';
  readonly profitNote = PROFIT_NOTE;
  readonly getStarted = GET_STARTED;
  readonly freeFeatures = FREE_PLAN_FEATURES;
  readonly freeLimitText = FREE_PLAN_LIMIT_TEXT;
  readonly proFeature = PRO_PLAN_FEATURE;
  readonly proPaymentLabel = PRO_PAYMENT_LABEL;
  readonly faq = FAQ;

  readonly period = signal<BillingPeriod>('annual');
  readonly menuCollapsed = signal(true);

  /** La sesión es del servicio de autenticación; la landing solo adapta el CTA. */
  readonly isAuthenticated = computed(() => this.authService.isAuthenticated);

  readonly primaryCtaLabel = computed(() =>
    this.isAuthenticated() ? 'Ir a mi panel' : 'Empezar gratis'
  );
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
