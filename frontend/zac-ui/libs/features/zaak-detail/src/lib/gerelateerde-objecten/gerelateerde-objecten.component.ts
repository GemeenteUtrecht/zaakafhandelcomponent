import { Component, OnInit } from '@angular/core';
import { Table } from '@gu/models';

@Component({
  selector: 'gu-gerelateerde-objecten',
  templateUrl: './gerelateerde-objecten.component.html',
  styleUrls: ['./gerelateerde-objecten.component.scss']
})
export class GerelateerdeObjectenComponent implements OnInit {

  tableData: Table = {
    headData: ['Status', 'Zaak ID', 'Behandelaar', 'Resultaat', 'Aard'],
    elementData: [
      {
        cellData: {
          status: "Ontvangen",
          zaakId: "2020-0000003594",
          behandelaar: "John Doe",
          resultaat: "Goed",
          aard: "Bijdrage"
        }
      },
      {
        cellData: {
          status: "Ontvangen",
          zaakId: "2020-0000003594",
          behandelaar: "John Doe",
          resultaat: "Goed",
          aard: "Bijdrage"
        }
      }
    ]
  }
  constructor() { }

  ngOnInit(): void {
  }

}
