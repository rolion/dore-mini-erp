import { Component } from '@angular/core';
import { NgbRating } from '@ng-bootstrap/ng-bootstrap';
import { RouterLink } from '@angular/router';

@Component({
    selector: 'app-ratings',
    templateUrl: './ratings.component.html',
    styleUrls: ['./ratings.component.sass'],
    imports: [RouterLink, NgbRating]
})
export class RatingsComponent {
  currentRate = 8;
  selected = 0;
  hovered = 0;
  readonly = false;
  currentRate2 = 3.14;
  constructor() {}
}
