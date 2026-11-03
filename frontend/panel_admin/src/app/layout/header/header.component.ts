import { DOCUMENT } from '@angular/common';
import {
  Component,
  ElementRef,
  OnInit,
  Renderer2,
  AfterViewInit,
  inject
} from '@angular/core';
import { Router } from '@angular/router';
import { NgbDropdown, NgbDropdownToggle, NgbDropdownMenu } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { FeatherModule } from 'angular-feather';
import { AuthService, InConfiguration, LocalStorageService, RightSidebarService } from '@core';
import { ConfigService } from '@config/config.service';
import { LanguageSelectorComponent } from '../../shared/components/language-selector/language-selector.component';
import { UserAvatarComponent } from '../../shared/components/user-avatar/user-avatar.component';
import { userFullName, userInitials } from '../../shared/models/user-profile';
import { APP_PATHS } from '../../core/routing/app-paths';


@Component({
    selector: 'app-header',
    templateUrl: './header.component.html',
    styleUrls: ['./header.component.sass'],
    imports: [
        FeatherModule,
        NgbDropdown,
        NgbDropdownToggle,
        NgbDropdownMenu,
        UserAvatarComponent,
        LanguageSelectorComponent,
        TranslatePipe,
    ],
    providers: [RightSidebarService]
})
export class HeaderComponent implements OnInit, AfterViewInit {
  public config!: InConfiguration;
  isNavbarCollapsed = true;
  isOpenSidebar?: boolean;
  docElement?: HTMLElement;
  isFullScreen = false;

  private document = inject(DOCUMENT);
  private renderer = inject(Renderer2);
  public elementRef = inject(ElementRef);
  private rightSidebarService = inject(RightSidebarService);
  private configService = inject(ConfigService);
  private authService = inject(AuthService);
  private router = inject(Router);
  private storageService = inject(LocalStorageService);

  ngOnInit() {
    this.config = this.configService.configData;
    this.docElement = this.document.documentElement;

  }
  ngAfterViewInit() {
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

    if (this.storageService.has('menuOption')) {
      this.renderer.addClass(
        this.document.body,
        this.storageService.get('menuOption') as string
      );
    } else {
      this.renderer.addClass(
        this.document.body,
        this.config.layout.sidebar.backgroundColor + '-sidebar'
      );
    }

    if (localStorage.getItem('sidebar_status')) {
      if (localStorage.getItem('sidebar_status') === 'close') {
        this.renderer.addClass(this.document.body, 'side-closed');
        this.renderer.addClass(this.document.body, 'submenu-closed');
      } else {
        this.renderer.removeClass(this.document.body, 'side-closed');
        this.renderer.removeClass(this.document.body, 'submenu-closed');
      }
    } else {
      if (this.config.layout.sidebar.collapsed === true) {
        this.renderer.addClass(this.document.body, 'side-closed');
        this.renderer.addClass(this.document.body, 'submenu-closed');
      }
    }
  }
  callFullscreen() {
    if (!this.isFullScreen) {
      if (this.docElement?.requestFullscreen != null) {
        this.docElement?.requestFullscreen();
      }
    } else {
      document.exitFullscreen();
    }
    this.isFullScreen = !this.isFullScreen;
  }
  mobileMenuSidebarOpen(event: Event, className: string) {
    if (window.innerWidth < 1025) {
      const hasClass = (event.target as HTMLInputElement).classList.contains(
        className
      );
      if (hasClass) {
        this.renderer.removeClass(this.document.body, className);
        this.renderer.addClass(this.document.body, 'sidebar-gone');
      } else {
        this.renderer.addClass(this.document.body, className);
        this.renderer.removeClass(this.document.body, 'sidebar-gone');
      }
    } else {
      const hasClass = this.document.body.classList.contains('side-closed');
      if (hasClass) {
        this.renderer.removeClass(this.document.body, 'side-closed');
        this.renderer.removeClass(this.document.body, 'submenu-closed');
      } else {
        this.renderer.addClass(this.document.body, 'side-closed');
        this.renderer.addClass(this.document.body, 'submenu-closed');
      }
    }
  }
  public toggleRightSidebar(): void {
    this.rightSidebarService.sidebarState.subscribe((isRunning) => {
      this.isOpenSidebar = isRunning;
    });

    this.rightSidebarService.setRightSidebar(
      (this.isOpenSidebar = !this.isOpenSidebar)
    );
  }
  /** Nombre y apellido de la sesión (con el usuario de respaldo); vacío si no hay sesión. */
  get userDisplayName(): string {
    return userFullName(this.authService.currentUserValue);
  }

  get userInitials(): string {
    return userInitials(this.authService.currentUserValue);
  }

  get companyName(): string {
    return this.authService.currentUserValue?.company?.name ?? '';
  }

  logout() {
    this.authService.logout().subscribe((res) => {
      if (!res.success) {
        this.router.navigate([APP_PATHS.login]);
      }
    });
  }
}
