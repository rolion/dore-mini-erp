import { Component } from '@angular/core';
import { FeatherModule } from 'angular-feather';
import { RouterLink } from '@angular/router';

@Component({
    selector: 'app-feather-icons',
    templateUrl: './feather-icons.component.html',
    styleUrls: ['./feather-icons.component.sass'],
    imports: [RouterLink, FeatherModule]
})
export class FeatherIconsComponent {
}
