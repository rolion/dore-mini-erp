import { Component } from '@angular/core';
import { NgbCollapse } from '@ng-bootstrap/ng-bootstrap';
import { RouterLink } from '@angular/router';

@Component({
    selector: 'app-collapse',
    templateUrl: './collapse.component.html',
    styleUrls: ['./collapse.component.sass'],
    imports: [RouterLink, NgbCollapse]
})
export class CollapseComponent {
  isCollapsed = false;
}
