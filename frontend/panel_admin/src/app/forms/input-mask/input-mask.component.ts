import { Component } from '@angular/core';
import { NgxMaskDirective, provideNgxMask } from 'ngx-mask';
import { RouterLink } from '@angular/router';

@Component({
    selector: 'app-input-mask',
    templateUrl: './input-mask.component.html',
    styleUrls: ['./input-mask.component.sass'],
    imports: [RouterLink, NgxMaskDirective],
    providers: [provideNgxMask()]
})
export class InputMaskComponent {

  constructor() { }



}
