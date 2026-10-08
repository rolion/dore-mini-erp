import { Component } from '@angular/core';
import { NgScrollbar } from 'ngx-scrollbar';
import { RouterLink } from '@angular/router';

@Component({
    selector: 'app-chat',
    templateUrl: './chat.component.html',
    styleUrls: ['./chat.component.scss'],
    imports: [RouterLink, NgScrollbar]
})
export class ChatComponent {
  constructor() {
    //constructor
  }
}
