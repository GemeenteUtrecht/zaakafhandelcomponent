import { Component, EventEmitter, Input, Output, ViewChild } from '@angular/core';
import { MatPaginator, PageEvent } from '@angular/material/paginator';

/**
 *     <gu-paginator (page)="onPageSelect($event)" [length]="resultLength"></gu-paginator>
 *
 *     Generic paginator component based on mat-paginator
 *
 *     Requires length: Total amount of results
 *     Takes pageSize: Number of results per page
 *
 *     Emits page: details about the paginator state
 */
@Component({
  selector: 'gu-paginator',
  templateUrl: './paginator.component.html'
})
export class PaginatorComponent {
  @ViewChild(MatPaginator) paginator: MatPaginator

  @Input() length = 0;
  @Input() pageSize = 100;

  @Output() page: EventEmitter<PageEvent> = new EventEmitter<PageEvent>();

  public firstPage() {
    this.paginator.firstPage();
  }
}
