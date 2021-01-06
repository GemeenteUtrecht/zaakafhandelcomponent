import { Component, Input } from '@angular/core';
import { Table } from '@gu/models';

@Component({
  selector: 'gu-table',
  templateUrl: './table.component.html',
  styleUrls: ['./table.component.scss']
})
export class TableComponent {

  @Input() expandable = false;
  @Input() tableData: Table;

  constructor() { }

  keepOriginalOrder = (a) => a.key

  expandRow(event) {
    const arrow = event.target;
    const parentRow = event.currentTarget.parentElement.parentElement;
    const childRow = parentRow.nextElementSibling;

    if (!childRow.classList.contains('child-row--expanded')) {
      childRow.classList.add('child-row--expanded');
    } else {
      childRow.classList.remove('child-row--expanded');
    }

    this.rotateArrow(arrow);
  }

  rotateArrow(arrow) {
    if (!arrow.classList.contains('arrow--rotated')) {
      arrow.classList.add('arrow--rotated');
    } else {
      arrow.classList.remove('arrow--rotated');
    }
  }

  isString(value) {
    return typeof value === 'string';
  }

  isObject(value) {
    return typeof value === 'object';
  }
}
