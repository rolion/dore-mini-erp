import { Component } from '@angular/core';
import { NgbProgressbar } from '@ng-bootstrap/ng-bootstrap';
import { RouterLink } from '@angular/router';

@Component({
    selector: 'app-progressbars',
    templateUrl: './progressbars.component.html',
    styleUrls: ['./progressbars.component.sass'],
    imports: [RouterLink, NgbProgressbar]
})
export class ProgressbarsComponent {
  height = '20px';
}
