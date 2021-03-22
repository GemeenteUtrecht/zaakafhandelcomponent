import { Component, Input, OnChanges } from '@angular/core';
import { RowData, Table, Zaak } from '@gu/models';

@Component({
  selector: 'gu-search-results',
  templateUrl: './search-results.component.html',
  styleUrls: ['./search-results.component.scss']
})
export class SearchResultsComponent implements OnChanges {
  @Input() resultData: Zaak[];

  tableData: Table = new Table([], []);

  constructor() { }

  ngOnChanges(): void {
    if (this.resultData) {
      this.tableData = this.createTableData(this.resultData);
    }
  }

  createTableData(resultData: Zaak[]): Table {
    const tableData: Table = new Table(['', 'Zaaknummer', 'Zaaktype', 'Omschrijving', 'Deadline'], []);

    // Add table body data
    tableData.bodyData = resultData.map( result => {
      const url = `/ui/zaken/${result.bronorganisatie}/${result.identificatie}`;
      const rowData: RowData = {
        cellData: {
          url: {
            type: 'link',
            label: 'Naar zaak',
            url: url
          },
          identificatie: result.identificatie,
          zaaktype: result.zaaktype.omschrijving,
          omschrijving: result.omschrijving,
          deadline: result.deadline,
        },
        expandData: result.toelichting
      }
      return rowData
    });

    return tableData
  }

}
