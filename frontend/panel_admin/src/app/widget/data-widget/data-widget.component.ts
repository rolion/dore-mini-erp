import { Component } from '@angular/core';
import { NgbProgressbar } from '@ng-bootstrap/ng-bootstrap';
import { NgScrollbar } from 'ngx-scrollbar';
import { RouterLink } from '@angular/router';

@Component({
    selector: 'app-data-widget',
    templateUrl: './data-widget.component.html',
    styleUrls: ['./data-widget.component.sass'],
    imports: [
        RouterLink,
        NgScrollbar,
        NgbProgressbar,
    ]
})
export class DataWidgetComponent {
  constructor() {
    //constructor
  }
}
