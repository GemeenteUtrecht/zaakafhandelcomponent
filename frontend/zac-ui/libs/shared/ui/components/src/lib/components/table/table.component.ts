import { Component, Input, Output, EventEmitter } from '@angular/core';
import { ExtensiveCell, Table } from '@gu/models';

@Component({
  selector: 'gu-table',
  templateUrl: './table.component.html',
  styleUrls: ['./table.component.scss']
})
export class TableComponent {

  @Input() expandable = false;
  @Input() tableData: Table;

  @Output() tableOutput = new EventEmitter<any>();
  @Output() buttonOutput = new EventEmitter<any>();

  constructor() { }

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

  expandRow(event) {
    if (this.expandable) {
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
}
