import { Component, ViewChild, HostListener } from '@angular/core';
import { DatatableComponent, NgxDatatableModule } from '@swimlane/ngx-datatable';
import { RouterLink } from '@angular/router';

export interface TableRow {
  id: number;
  img: string;
  name: string;
  designation: string;
  gender: string;
  phone: string;
  email: string;
  status: string;
  age: number;
  address: {
    state: string;
    city: string;
  };
}

@Component({
    selector: 'app-row-details',
    templateUrl: './row-details.component.html',
    styleUrls: ['./row-details.component.sass'],
    imports: [RouterLink, NgxDatatableModule]
})
export class RowDetailsComponent {
  rows: TableRow[] = [];
  expanded: Record<string, boolean> = {};
  timeout: ReturnType<typeof setTimeout> | undefined;
  loadingIndicator = true;
  reorderable = true;
  scrollBarHorizontal = window.innerWidth < 1200;

  @ViewChild('table') table!: DatatableComponent;

  constructor() {
    this.fetch((data: TableRow[]) => {
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

  onPage(event: unknown) {
    clearTimeout(this.timeout);
    this.timeout = setTimeout(() => {
      console.log('paged!', event);
    }, 100);
  }

  getRowHeight(row: { height: number }) {
    return row.height;
  }
  fetch(cb: (data: TableRow[]) => void) {
    const req = new XMLHttpRequest();
    req.open('GET', `assets/data/detail-row-data.json`);

    req.onload = () => {
      cb(JSON.parse(req.response));
    };

    req.send();
  }
  toggleExpandRow(row: TableRow) {
    console.log('Toggled Expand Row!', row);
    this.table.rowDetail?.toggleExpandRow(row);
  }

  onDetailToggle(event: unknown) {
    console.log('Detail Toggled', event);
  }
}
