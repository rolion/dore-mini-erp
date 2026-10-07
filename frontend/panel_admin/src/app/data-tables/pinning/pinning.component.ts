import { Component, ViewChild, HostListener } from '@angular/core';
import { DatatableComponent, NgxDatatableModule } from '@swimlane/ngx-datatable';
import { RouterLink } from '@angular/router';

@Component({
    selector: 'app-pinning',
    templateUrl: './pinning.component.html',
    styleUrls: ['./pinning.component.sass'],
    imports: [RouterLink, NgxDatatableModule]
})
export class PinningComponent {
  rows = [];
  loadingIndicator = true;
  reorderable = true;
  scrollBarHorizontal = window.innerWidth < 1200;

  @ViewChild('table') table!: DatatableComponent;

  constructor() {
    this.fetch((data: never[]) => {
      this.rows = data;
      setTimeout(() => {
        this.loadingIndicator = false;
      }, 500);
    });
  }

  @HostListener('window:resize')
  onResize() {
    this.scrollBarHorizontal = window.innerWidth < 1200;
    this.table.recalculate();
    this.table.recalculateColumns();
  }

  getRowHeight(row: { height: number }) {
    return row.height;
  }
  fetch(cb: (data: never[]) => void) {
    const req = new XMLHttpRequest();
    req.open('GET', `assets/data/datatable-data.json`);

    req.onload = () => {
      cb(JSON.parse(req.response));
    };

    req.send();
  }
}
