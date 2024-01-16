import {Component, EventEmitter, Input, OnChanges, Output, SimpleChanges} from '@angular/core';
import {RowData, Table, Zaak} from '@gu/models';
import {tableHead} from './constants/table';
import {PageEvent} from '@angular/material/paginator';

@Component({
  selector: 'gu-search-results',
  templateUrl: './search-results.component.html',
  styleUrls: ['./search-results.component.scss']
})
export class SearchResultsComponent implements OnChanges {
  @Input() resultData: Zaak[];
  @Input() resultLength: number;
  @Input() controlled = false;

  @Output() sortOutput = new EventEmitter<any>();
  @Output() tableOutput = new EventEmitter<any>();
  @Output() pageOutput = new EventEmitter<PageEvent>();

  tableData: Table = new Table([], []);

  constructor() {}

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.resultData) {
      this.tableData = this.createTableData(changes.resultData.currentValue);
    }
  }

  resetTable() {

  }

  createTableData(resultData: Zaak[]): Table {
    const tableData: Table = new Table(tableHead, []);

    // Add table body data
    tableData.bodyData = resultData.map(result => {
      const url = (this.controlled) ? '#' : `/ui/zaken/${result.bronorganisatie}/${result.identificatie}`;
      const rowData: RowData = {
        cellData: {
          url: {
            type: this.controlled ? 'text': 'link',
            label: result.identificatie,
            url: url
          },
          zaaktype: result.zaaktype.omschrijving,
          omschrijving: result.omschrijving,
          deadline: {
            type: result.deadline ? 'date' : 'text',
            date: result.deadline
          }
        },
        ...(result.toelichting?.length > 0) && {expandData: result.toelichting},
        clickOutput: result,
      }
      return rowData
    });

    return tableData
  }

}
