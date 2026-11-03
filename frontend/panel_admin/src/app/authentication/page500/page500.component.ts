import { TranslatePipe } from '@ngx-translate/core';
import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';

@Component({
    selector: 'app-page500',
    templateUrl: './page500.component.html',
    styleUrls: ['./page500.component.sass'],
    imports: [TranslatePipe, FormsModule, RouterLink]
})
export class Page500Component {

  constructor() { }

}
