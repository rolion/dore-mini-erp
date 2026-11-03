import { TranslatePipe } from '@ngx-translate/core';
import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';

@Component({
    selector: 'app-page404',
    templateUrl: './page404.component.html',
    styleUrls: ['./page404.component.sass'],
    imports: [TranslatePipe, FormsModule, RouterLink]
})
export class Page404Component {

  constructor() { }

}
