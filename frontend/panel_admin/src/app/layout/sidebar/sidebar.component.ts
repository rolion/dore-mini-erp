import {
  Router,
  NavigationEnd,
  RouterLink,
  RouterLinkActive,
} from '@angular/router';
import { NgClass, DOCUMENT } from '@angular/common';
import {
  Component,
  DestroyRef,
  ElementRef,
  OnInit,
  Renderer2,
  HostListener,
  OnDestroy,
  inject,
} from '@angular/core';
import { RouteInfo } from './sidebar.metadata';
import { TranslateModule } from '@ngx-translate/core';
import { FeatherModule } from 'angular-feather';
import { NgScrollbar } from 'ngx-scrollbar';
import { AuthService } from '@core';
import { UserAvatarComponent } from '../../shared/components/user-avatar/user-avatar.component';
import { userFullName, userInitials } from '../../shared/models/user-profile';
import { SidebarService } from './sidebar.service';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Subscription, combineLatest } from 'rxjs';
import { ModulesService } from '../../core/service/modules.service';
import { filterMenu } from './menu-filter';

@Component({
  selector: 'app-sidebar',
  templateUrl: './sidebar.component.html',
  styleUrls: ['./sidebar.component.sass'],
  imports: [
    RouterLink,
    NgScrollbar,
    RouterLinkActive,
    NgClass,
    FeatherModule,
    TranslateModule,
    UserAvatarComponent,
  ],
})
export class SidebarComponent implements OnInit, OnDestroy {
  public sidebarItems!: RouteInfo[];
  public innerHeight?: number;
  private readonly exactMatch = { exact: true };
  private readonly prefixMatch = { exact: false };
  public bodyTag!: HTMLElement;
  listMaxHeight?: string;
  listMaxWidth?: string;
  headerHeight = 60;
  currentRoute?: string;
  routerObj: Subscription;

  private document = inject(DOCUMENT);
  private renderer = inject(Renderer2);
  public elementRef = inject(ElementRef);
  private authService = inject(AuthService);
  private router = inject(Router);
  private sidebarService = inject(SidebarService);
  private modulesService = inject(ModulesService);
  private destroyRef = inject(DestroyRef);

  constructor() {
    this.routerObj = this.router.events.subscribe((event) => {
      if (event instanceof NavigationEnd) {
        // close sidebar on mobile screen after menu select
        this.renderer.removeClass(this.document.body, 'overlay-open');
        this.sidebbarClose();
      }
    });
  }
  @HostListener('window:resize')
  windowResizecall() {
    if (window.innerWidth < 1025) {
      this.renderer.removeClass(this.document.body, 'side-closed');
    }
    this.setMenuHeight();
    this.checkStatuForResize(false);
  }
  @HostListener('document:mousedown', ['$event'])
  onGlobalClick(event: Event): void {
    if (!this.elementRef.nativeElement.contains(event.target)) {
      this.renderer.removeClass(this.document.body, 'overlay-open');
      this.sidebbarClose();
    }
  }
  /**
   * Un ítem se marca activo por prefijo de ruta; si un hermano extiende su ruta
   * (p. ej. `/pocketbiz/expenses` y `/pocketbiz/expenses/categories`) se exige coincidencia exacta para
   * que quede un único ítem resaltado.
   */
  linkActiveOptions(item: RouteInfo, siblings: RouteInfo[]): { exact: boolean } {
    const shadowed =
      item.path !== '' &&
      siblings.some((sibling) => sibling !== item && sibling.path.startsWith(item.path + '/'));
    return shadowed ? this.exactMatch : this.prefixMatch;
  }
  callToggleMenu(event: Event, length: number) {
    if (length > 0) {
      const parentElement = (event.target as HTMLInputElement).closest('li');
      const activeClass = parentElement?.classList.contains('active');

      if (activeClass) {
        this.renderer.removeClass(parentElement, 'active');
      } else {
        this.renderer.addClass(parentElement, 'active');
      }
    }
  }
  ngOnInit() {
    if (this.authService.currentUserValue) {
      // Mientras no se conocen los módulos solo se ven los ítems sin módulo; ante un error, solo los base.
      this.modulesService.loadQuietly().pipe(takeUntilDestroyed(this.destroyRef)).subscribe();
      combineLatest([this.sidebarService.getRouteInfo(), this.modulesService.enabledKeys$])
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe(([routes, enabled]) => {
          this.sidebarItems = filterMenu(routes, enabled);
        });
    }
    this.initLeftSidebar();
    this.bodyTag = this.document.body;
  }
  ngOnDestroy() {
    this.routerObj.unsubscribe();
  }
  initLeftSidebar() {
    // eslint-disable-next-line @typescript-eslint/no-this-alias
    const _this = this;
    // Set menu height
    _this.setMenuHeight();
    _this.checkStatuForResize(true);
  }
  setMenuHeight() {
    this.innerHeight = window.innerHeight;
    const height = this.innerHeight - this.headerHeight;
    this.listMaxHeight = height + '';
    this.listMaxWidth = '500px';
  }
  isOpen() {
    return this.bodyTag.classList.contains('overlay-open');
  }
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  checkStatuForResize(firstTime: boolean) {
    if (window.innerWidth < 1025) {
      this.renderer.addClass(this.document.body, 'sidebar-gone');
    } else {
      this.renderer.removeClass(this.document.body, 'sidebar-gone');
    }
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

  mouseHover() {
    const body = this.elementRef.nativeElement.closest('body');
    if (body.classList.contains('submenu-closed')) {
      this.renderer.addClass(this.document.body, 'side-closed-hover');
      this.renderer.removeClass(this.document.body, 'submenu-closed');
    }
  }
  mouseOut() {
    const body = this.elementRef.nativeElement.closest('body');
    if (body.classList.contains('side-closed-hover')) {
      this.renderer.removeClass(this.document.body, 'side-closed-hover');
      this.renderer.addClass(this.document.body, 'submenu-closed');
    }
  }

  sidebbarClose() {
    if (window.innerWidth < 1025) {
      this.renderer.addClass(this.document.body, 'sidebar-gone');
    }
  }
}
