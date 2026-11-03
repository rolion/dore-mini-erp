import { TranslatePipe } from '@ngx-translate/core';
import { Component } from '@angular/core';
import { FeatherModule } from 'angular-feather';

@Component({
    selector: 'app-footer',
    templateUrl: './footer.component.html',
    styleUrls: ['./footer.component.sass'],
    imports: [TranslatePipe, FeatherModule]
})
export class FooterComponent {
}
