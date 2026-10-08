import { Component } from '@angular/core';
import { NgbProgressbar, NgbNav, NgbNavItem, NgbNavItemRole, NgbNavLinkBase, NgbNavLink, NgbNavContent, NgbNavOutlet } from '@ng-bootstrap/ng-bootstrap';
import { RouterLink } from '@angular/router';

@Component({
    selector: 'app-profile',
    templateUrl: './profile.component.html',
    styleUrls: ['./profile.component.sass'],
    imports: [
        RouterLink,
        NgbProgressbar,
        NgbNav,
        NgbNavItem,
        NgbNavItemRole,
        NgbNavLinkBase,
        NgbNavLink,
        NgbNavContent,
        NgbNavOutlet,
    ]
})
export class ProfileComponent {
  active!: number;
  constructor() {
    //constructor
  }
}
