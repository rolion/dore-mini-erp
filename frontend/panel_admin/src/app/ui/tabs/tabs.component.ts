import { Component } from '@angular/core';
import { NgbNavChangeEvent, NgbNav, NgbNavItem, NgbNavItemRole, NgbNavLinkBase, NgbNavLink, NgbNavContent, NgbNavOutlet, NgbDropdown, NgbDropdownToggle, NgbDropdownMenu, NgbDropdownItem } from '@ng-bootstrap/ng-bootstrap';
import { RouterLink } from '@angular/router';

@Component({
    selector: 'app-tabs',
    templateUrl: './tabs.component.html',
    styleUrls: ['./tabs.component.sass'],
    imports: [
        RouterLink,
        NgbNav,
        NgbNavItem,
        NgbNavItemRole,
        NgbNavLinkBase,
        NgbNavLink,
        NgbNavContent,
        NgbNavOutlet,
        NgbDropdown,
        NgbDropdownToggle,
        NgbDropdownMenu,
        NgbDropdownItem,
    ]
})
export class TabsComponent {
  active: string | number | undefined;
  active2 = 'top';
  active3!: number;
  active4: string | number | undefined;
  disabled = true;
  content1 =
    'Raw denim you probably have not heard of them jean shorts Austin. Nesciunt tofu stumptown aliqua, retro' +
    'synth master cleanse. Mustache cliche tempor, williamsburg carles vegan helvetica. Reprehenderit butcher retro' +
    'keffiyeh dreamcatcher synth. Cosby sweater eu banh mi, qui irure terry richardson ex squid. Aliquip placeat' +
    'salvia cillum iphone. Seitan aliquip quis cardigan american apparel, butcher voluptate nisi qui.';

  content2 =
    'Food truck fixie locavore, accusamus mcsweeney marfa nulla single-origin coffee squid.' +
    'Exercitation +1 labore velit, blog sartorial PBR leggings next level wes anderson artisan four loko farm-to-table craft beer twee. Qui photo booth letterpress, commodo enim craft beer mlkshk aliquip jean shorts ullamco ad vinyl cillum PBR. Homo nostrud organic, assumenda labore aesthetic magna delectus mollit. Keytar helvetica VHS salvia yr, vero magna velit sapiente labore stumptown. Vegan fanny pack odio cillum wes anderson 8-bit, sustainable jean shorts beard ut DIY ethical culpa terry richardson biodiesel. Art party scenester stumptown, tumblr butcher vero sint qui sapiente accusamus tattooed echo park.';

  content3 =
    'Sed commodo, leo at suscipit dictum, quam est porttitor sapien, eget sodales nibh elit id diam. Nulla' +
    'facilisi. Donec egestas ligula vitae odio interdum aliquet. Duis lectus turpis, luctus eget tincidunt' +
    'eu, congue et odio. Duis pharetra et nisl at faucibus. Quisque luctus pulvinar arcu, et molestie lectus' +
    'ultrices et. Sed diam urna, egestas ut ipsum vel, volutpat volutpat neque. Praesent fringilla tortor' +
    'arcu. Vivamus faucibus nisl enim, nec tristique ipsum euismod facilisis. Morbi ut bibendum est, eu' +
    'tincidunt odio. Orci varius natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus.' +
    'Mauris aliquet odio ac lorem aliquet ultricies in eget neque. Phasellus nec tortor vel tellus pulvinar' +
    'feugiat.';

  onNavChange(changeEvent: NgbNavChangeEvent) {
    if (changeEvent.nextId === 3) {
      changeEvent.preventDefault();
    }
  }

  toggleDisabled() {
    this.disabled = !this.disabled;
    if (this.disabled) {
      this.active3 = 1;
    }
  }
}
