import { Component, EventEmitter, Input, OnChanges, Output } from '@angular/core';
import { RowData, Table, Zaak } from '@gu/models';
import { tableHead } from './constants/table';

@Component({
  selector: 'gu-search-results',
  templateUrl: './search-results.component.html',
  styleUrls: ['./search-results.component.scss']
})
export class SearchResultsComponent implements OnChanges {
  @Input() resultData: Zaak[];
  @Output() sortOutput = new EventEmitter<any>();

  tableData: Table = new Table([], []);

  constructor() { }

  ngOnChanges(): void {
    if (this.resultData) {
      this.tableData = this.createTableData(this.resultData);
    }
  }

  createTableData(resultData: Zaak[]): Table {
    const tableData: Table = new Table(tableHead, []);

    // Add table body data
    tableData.bodyData = resultData.map( result => {
      const url = `/ui/zaken/${result.bronorganisatie}/${result.identificatie}`;
      const rowData: RowData = {
        cellData: {
          url: {
            type: 'link',
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
        expandData: result.toelichting
      }
      return rowData
    });

    return tableData
  }

}
