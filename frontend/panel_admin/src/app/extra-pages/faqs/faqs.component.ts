import { FAQS } from './faqs.model';
import { FaqService } from './faq.service';
import { Component, inject } from '@angular/core';
import { NgbAccordionModule } from '@ng-bootstrap/ng-bootstrap';
import { RouterLink } from '@angular/router';
@Component({
    selector: 'app-faqs',
    templateUrl: './faqs.component.html',
    styleUrls: ['./faqs.component.sass'],
    providers: [FaqService],
    imports: [
        RouterLink,
        NgbAccordionModule
    ]
})
export class FaqsComponent {
  private faqService = inject(FaqService);
  faqs: FAQS[] = this.faqService.faqs;
  searchString!: string;

  filter(event: Event) {
    this.searchString = (event.target as HTMLInputElement).value;
    if ((event.target as HTMLInputElement).value === '') {
      this.faqs = this.faqService.faqs;
    } else {
      this.faqs = this.faqService.faqs.filter(
        (faqs: FAQS) =>
          faqs.title.toUpperCase().indexOf(this.searchString.toUpperCase()) !==
          -1 ||
          faqs.content
            .toUpperCase()
            .indexOf(this.searchString.toUpperCase()) !== -1
      );
    }
  }
}
