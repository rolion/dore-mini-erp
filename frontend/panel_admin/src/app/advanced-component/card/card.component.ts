import { Component } from '@angular/core';
import { NgbCollapse } from '@ng-bootstrap/ng-bootstrap';
import { RouterLink } from '@angular/router';

@Component({
    selector: 'app-card',
    templateUrl: './card.component.html',
    styleUrls: ['./card.component.sass'],
    imports: [RouterLink, NgbCollapse]
})
export class CardComponent {
  public isCollapsed = false;
}
