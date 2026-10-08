import { Component, inject } from '@angular/core';
import { NgbCarouselConfig, NgbCarousel, NgbSlide } from '@ng-bootstrap/ng-bootstrap';
import { RouterLink } from '@angular/router';

@Component({
    selector: 'app-carousel',
    templateUrl: './carousel.component.html',
    styleUrls: ['./carousel.component.sass'],
    providers: [NgbCarouselConfig],
    imports: [
        RouterLink,
        NgbCarousel,
        NgbSlide,
    ]
})
export class CarouselComponent {
  showNavigationArrows = false;
  showNavigationIndicators = false;
  images = [1, 2, 3].map((n) => `assets/images/carousel/${n}.jpg`);

  private config = inject(NgbCarouselConfig);

  constructor() {
    // customize default values of carousels used by this component tree
    this.config.showNavigationArrows = true;
    this.config.showNavigationIndicators = true;
  }
}
