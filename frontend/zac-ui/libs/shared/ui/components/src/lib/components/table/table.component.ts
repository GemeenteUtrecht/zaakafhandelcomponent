import { Component, Input, Output, EventEmitter } from '@angular/core';
import { ExtensiveCell, Table, TableSort } from '@gu/models';


@Component({
  selector: 'gu-table',
  templateUrl: './table.component.html',
  styleUrls: ['./table.component.scss']
})

export class TableComponent {

  @Input() expandable = false;
  @Input() sortable = false;
  @Input() tableData: Table;
  @Input() headColor: 'gray';

  @Output() tableOutput = new EventEmitter<any>();
  @Output() buttonOutput = new EventEmitter<any>();
  @Output() sortOutput = new EventEmitter<any>();

  sortValue: string;
  sortOrder: 'asc' | 'desc';

  keepOriginalOrder = (a) => a.key

  handleRowClickOutput(value) {
    if (value) {
      this.tableOutput.emit(value);
    }
  }

  handleButtonClick(key, value) {
    if (key && value) {
      this.buttonOutput.emit(
        {[key]: value}
      )
    }
  }

  handleNestedButtonClick(event) {
    this.buttonOutput.emit(event);
  }

  expandRow(event, expandData: string) {
    if (this.expandable && expandData) {
      const clickedElement = event.target;
      const parentRow = clickedElement.closest('tr.parent-row')
      const arrowElement = parentRow.querySelector('.arrow');
      const childRow = parentRow.nextElementSibling;

      if (!childRow.classList.contains('child-row--expanded')) {
        childRow.classList.add('child-row--expanded');
      } else {
        childRow.classList.remove('child-row--expanded');
      }

      this.rotateArrow(arrowElement);
    }
  }

  expandNestedTable(event, tableData: Table) {
    if (this.expandable && tableData) {
      this.expandRow(event, 'expand')
    }
  }

  rotateArrow(element) {
    if (!element.classList.contains('arrow--rotated')) {
      element.classList.add('arrow--rotated');
    } else {
      element.classList.remove('arrow--rotated');
    }
  }

  isString(value) {
    return typeof value === 'string';
  }

  checkCellType(value: ExtensiveCell | string) {
    if (!!value) {
      if (typeof value === 'object') {
        return value.type;
      }
    }
  }

  outputSort(headValue) {
    if (headValue !== this.sortValue) {
      this.sortValue = headValue;
      this.sortOrder = 'asc'
    }
    else if (headValue === this.sortValue) {
      this.sortOrder = this.sortOrder === 'asc' ? 'desc' : 'asc';
    }
    const output: TableSort = {
      value: this.sortValue,
      order: this.sortOrder
    }
    this.sortOutput.emit(output);
  }
}
