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
  address: string;
}

@Component({
    selector: 'app-filter',
    templateUrl: './filter.component.html',
    styleUrls: ['./filter.component.sass'],
    imports: [RouterLink, NgxDatatableModule]
})
export class FilterComponent {
  rows: TableRow[] = [];
  temp: TableRow[] = [];
  loadingIndicator = true;
  reorderable = true;
  scrollBarHorizontal = window.innerWidth < 1200;

  @ViewChild('table') table!: DatatableComponent;

  constructor() {
    this.fetch((data: TableRow[]) => {
      this.temp = [...data];
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
  fetch(cb: (data: TableRow[]) => void) {
    const req = new XMLHttpRequest();
    req.open('GET', `assets/data/datatable-data.json`);

    req.onload = () => {
      cb(JSON.parse(req.response));
    };

    req.send();
  }

  updateFilter(event: Event) {
    const input = event.target as HTMLInputElement;
    const val = input.value.toLowerCase();

    // filter our data
    const temp = this.temp.filter(function (d: TableRow) {
      return d.name.toLowerCase().indexOf(val) !== -1 || !val;
    });

    // update the rows
    this.rows = temp;
    // Whenever the filter changes, always go back to the first page
    this.table.offset = 0;
  }
}
