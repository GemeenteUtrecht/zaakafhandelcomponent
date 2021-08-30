import { Component, EventEmitter, Input, Output } from '@angular/core';
import { PageEvent } from '@angular/material/paginator';

/**
 *     <gu-paginator (page)="onPageSelect($event)" [length]="resultLength"></gu-paginator>
 *
 *     Generic paginator componentm based on mat-paginator
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

  @Input() length = 0;
  @Input() pageSize = 100;

  @Output() page: EventEmitter<PageEvent> = new EventEmitter<PageEvent>();
}
