import { Component, OnInit } from '@angular/core';
import { Table } from '@gu/models';

@Component({
  selector: 'gu-gerelateerde-zaken',
  templateUrl: './gerelateerde-zaken.component.html',
  styleUrls: ['./gerelateerde-zaken.component.scss']
})
export class GerelateerdeZakenComponent implements OnInit {

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
