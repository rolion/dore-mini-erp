import { TranslatePipe } from '@ngx-translate/core';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';

@Component({
    selector: 'app-reset',
    templateUrl: './reset.component.html',
    styleUrls: ['./reset.component.sass'],
    imports: [TranslatePipe, FormsModule]
})
export class ResetComponent {

  constructor() { }

}
