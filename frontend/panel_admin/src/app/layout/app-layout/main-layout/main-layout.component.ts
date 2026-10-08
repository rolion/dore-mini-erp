import { Direction } from '@angular/cdk/bidi';
import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { RightSidebarComponent } from '../../right-sidebar/right-sidebar.component';
import { SidebarComponent } from '../../sidebar/sidebar.component';
import { HeaderComponent } from '../../header/header.component';
import { DirectionService, InConfiguration, LocalStorageService } from '@core';
import { ConfigService } from '@config/config.service';

@Component({
    selector: 'app-main-layout',
    templateUrl: './main-layout.component.html',
    styleUrls: [],
    imports: [
        HeaderComponent,
        SidebarComponent,
        RightSidebarComponent,
        RouterOutlet,
    ]
})
export class MainLayoutComponent {
  direction!: Direction;
  public config!: InConfiguration;

  private directoryService = inject(DirectionService);
  private configService = inject(ConfigService);
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
  }
}
