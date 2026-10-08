import { Component, inject } from '@angular/core';
import { ToastrService } from 'ngx-toastr';
import { RouterLink } from '@angular/router';
@Component({
    selector: 'app-toast',
    templateUrl: './toast.component.html',
    styleUrls: ['./toast.component.sass'],
    providers: [ToastrService],
    imports: [RouterLink]
})
export class ToastComponent {
  private toastr = inject(ToastrService);
  constructor() {}

  showSuccess() {
    this.toastr.success('Success Message Here.', 'Success Title!');
  }

  showInfo() {
    this.toastr.info('Info Message Here.', 'Info Title!');
  }

  showWarning() {
    this.toastr.warning('Warning Message Here.', 'Warning Title!');
  }

  showError() {
    this.toastr.error('Error Message Here.', 'Error Title!');
  }

  showCustom() {
    this.toastr.success('<span class="col-cyan">Font Color Cyan.</span>', '', {
      enableHtml: true,
    });
  }
  progressBar() {
    this.toastr.success('Progress bar example.', 'Hello', {
      progressBar: true,
    });
  }
  showCloseButton() {
    this.toastr.info('Close Button Example', 'Close Titile', {
      closeButton: true,
    });
  }
  showTimeout() {
    this.toastr.error('close after 2 seconds.', 'Timeout!', { timeOut: 2000 });
  }
  topLeft() {
    this.toastr.success('Success Message Here.', 'Success Title!', {
      positionClass: 'toast-top-left',
    });
  }
  bottomLeft() {
    this.toastr.success('Success Message Here.', 'Success Title!', {
      positionClass: 'toast-bottom-left',
    });
  }
  bottomRight() {
    this.toastr.success('Success Message Here.', 'Success Title!', {
      positionClass: 'toast-bottom-right',
    });
  }

  topCenter() {
    this.toastr.success('Success Message Here.', 'Success Title!', {
      positionClass: 'toast-top-center',
    });
  }
}
