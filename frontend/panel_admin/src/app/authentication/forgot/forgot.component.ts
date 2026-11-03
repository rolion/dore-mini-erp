import { TranslatePipe } from '@ngx-translate/core';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';

@Component({
    selector: 'app-forgot',
    templateUrl: './forgot.component.html',
    styleUrls: ['./forgot.component.sass'],
    imports: [TranslatePipe, FormsModule]
})
export class ForgotComponent {
}
