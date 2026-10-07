import { Component } from '@angular/core';
import { NgbAccordionModule } from '@ng-bootstrap/ng-bootstrap';
import { RouterLink } from '@angular/router';

@Component({
    selector: 'app-accordion',
    templateUrl: './accordion.component.html',
    styleUrls: ['./accordion.component.sass'],
    imports: [
        RouterLink,
        NgbAccordionModule
    ]
})
export class AccordionComponent {
  acc: unknown;
  disabled = false;
  items = ['First', 'Second', 'Third'];
  content =
    'Anim pariatur cliche reprehenderit, enim eiusmod high life accusamus terry richardson ad squid. 3 wolf' +
    'moon officia aute, non cupidatat skateboard dolor brunch. Food truck quinoa nesciunt laborum eiusmod.' +
    'Brunch 3 wolf moon tempor, sunt aliqua put a bird on it squid single-origin coffee nulla assumenda' +
    'shoreditch et. Nihil anim keffiyeh helvetica,';
}
