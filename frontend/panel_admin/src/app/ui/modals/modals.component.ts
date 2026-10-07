import { Component, ViewEncapsulation, Input, inject, TemplateRef } from '@angular/core';
import {
  NgbModal,
  ModalDismissReasons,
  NgbActiveModal,
} from '@ng-bootstrap/ng-bootstrap';
import { RouterLink } from '@angular/router';

@Component({
    selector: 'app-ngbd-modal-content',
    template: `
    <div class="modal-header">
      <h4 class="modal-title">Hi there!</h4>
      <button
        type="button"
        class="close"
        aria-label="Close"
        (click)="activeModal.dismiss('Cross click')"
      >
        <span aria-hidden="true">&times;</span>
      </button>
    </div>
    <div class="modal-body">
      <p>Hello, {{ name }}!</p>
    </div>
    <div class="modal-footer">
      <button
        type="button"
        class="btn btn-secondary btn-raised"
        (click)="activeModal.close('Close click')"
      >
        Close
      </button>
    </div>
  `,
})
// eslint-disable-next-line @angular-eslint/component-class-suffix
export class NgbdModalContent {
  @Input() name: string | undefined;
  public activeModal = inject(NgbActiveModal);
}

@Component({
    selector: 'app-modals',
    templateUrl: './modals.component.html',
    styleUrls: ['./modals.component.sass'],
    encapsulation: ViewEncapsulation.None,
    styles: [
        `
      .dark-modal .modal-content {
        background-color: #292b2c;
        color: white;
      }
      .dark-modal .close {
        color: white;
      }
      .light-blue-backdrop {
        background-color: #5cb3fd;
      }
    `,
    ],
    imports: [RouterLink]
})
export class ModalsComponent {
  closeResult!: string;
  private modalService = inject(NgbModal);

  open(content: string | TemplateRef<unknown>) {
    this.modalService.open(content).result.then(
      (result) => {
        this.closeResult = `Closed with: ${result}`;
      },
      (reason) => {
        this.closeResult = `Dismissed ${this.getDismissReason(reason)}`;
      }
    );
  }

  private getDismissReason(reason: unknown): string {
    if (reason === ModalDismissReasons.ESC) {
      return 'by pressing ESC';
    } else if (reason === ModalDismissReasons.BACKDROP_CLICK) {
      return 'by clicking on a backdrop';
    } else {
      return `with: ${reason}`;
    }
  }

  openContent() {
    const modalRef = this.modalService.open(NgbdModalContent);
    modalRef.componentInstance.name = 'World';
  }

  openBackDropCustomClass(content: string | TemplateRef<unknown>) {
    this.modalService.open(content, { backdropClass: 'light-blue-backdrop' });
  }

  openWindowCustomClass(content: string | TemplateRef<unknown>) {
    this.modalService.open(content, { windowClass: 'dark-modal' });
  }

  openSm(content: string | TemplateRef<unknown>) {
    this.modalService.open(content, { size: 'sm' });
  }

  openLg(content: string | TemplateRef<unknown>) {
    this.modalService.open(content, { size: 'lg' });
  }

  openXl(content: string | TemplateRef<unknown>) {
    this.modalService.open(content, { size: 'xl' });
  }

  openVerticallyCentered(content: string | TemplateRef<unknown>) {
    this.modalService.open(content, { centered: true });
  }

  openScrollableContent(longContent: string | TemplateRef<unknown>) {
    this.modalService.open(longContent, { scrollable: true });
  }
}
