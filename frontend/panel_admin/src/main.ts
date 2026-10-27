import { provideZoneChangeDetection } from "@angular/core";

import { bootstrapApplication } from '@angular/platform-browser';
import { AppComponent } from 'app/app.component';
import { appConfig } from 'app/app.config';
import { redirectLegacyHash } from 'app/core/routing/legacy-hash-redirect';

// URLs antiguas con hash (/#/ruta) → /ruta, antes de que arranque el router.
redirectLegacyHash(window);

bootstrapApplication(AppComponent, {...appConfig, providers: [provideZoneChangeDetection(), ...appConfig.providers]})
  .catch(err => console.error(err));
