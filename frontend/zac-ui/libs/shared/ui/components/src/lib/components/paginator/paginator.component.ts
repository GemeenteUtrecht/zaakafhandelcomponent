import { Component, EventEmitter, Input, Output } from '@angular/core';
import { PageEvent } from '@angular/material/paginator';

@Component({
  selector: 'gu-paginator',
  templateUrl: './paginator.component.html',
  styleUrls: ['./paginator.component.scss']
})
export class PaginatorComponent {

  // MatPaginator Inputs
  @Input() length = 0;
  @Input() pageSize = 100;

  @Output() page: EventEmitter<PageEvent> = new EventEmitter<PageEvent>();
}
