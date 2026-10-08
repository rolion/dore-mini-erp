import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';

@Component({
    selector: 'app-page404',
    templateUrl: './page404.component.html',
    styleUrls: ['./page404.component.sass'],
    imports: [FormsModule, RouterLink]
})
export class Page404Component {

  constructor() { }

}
