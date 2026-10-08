import { Direction } from '@angular/cdk/bidi';
import { Component, Renderer2, DOCUMENT, inject } from '@angular/core';

import { RouterOutlet } from '@angular/router';
import { DirectionService, InConfiguration, LocalStorageService } from '@core';
import { ConfigService } from '@config/config.service';

@Component({
    selector: 'app-auth-layout',
    templateUrl: './auth-layout.component.html',
    styleUrls: [],
    imports: [RouterOutlet]
})
export class AuthLayoutComponent {
  direction!: Direction;
  public config!: InConfiguration;

  private document = inject(DOCUMENT);
  private directoryService = inject(DirectionService);
  private configService = inject(ConfigService);
  private renderer = inject(Renderer2);
  private storageService = inject(LocalStorageService);

  constructor() {
    this.config = this.configService.configData;
    this.directoryService.currentData.subscribe((currentData) => {
      if (currentData) {
        this.direction = currentData === 'ltr' ? 'ltr' : 'rtl';
      } else {
        if (this.storageService.has('isRtl')) {
          if (this.storageService.get('isRtl') as string === 'true') {
            this.direction = 'rtl';
          } else if (this.storageService.get('isRtl') as string === 'false') {
            this.direction = 'ltr';
          }
        }
      }
    });

    // set theme on startup
    if (this.storageService.has('theme')) {
      this.renderer.removeClass(this.document.body, this.config.layout.variant);
      this.renderer.addClass(
        this.document.body,
        this.storageService.get('theme') as string
      );
    } else {
      this.renderer.addClass(this.document.body, this.config.layout.variant);
    }
  }
}
