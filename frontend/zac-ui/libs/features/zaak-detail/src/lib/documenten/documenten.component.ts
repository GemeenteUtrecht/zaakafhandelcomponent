import { Component, OnInit } from '@angular/core';
import { Table } from '@gu/models';

@Component({
  selector: 'gu-documenten',
  templateUrl: './documenten.component.html',
  styleUrls: ['./documenten.component.scss']
})
export class DocumentenComponent implements OnInit {
  tableData: Table = {
    headData: ['Type', 'Bestandsnaam', 'Vertrouwelijkheid', 'Aanmaakdatum'],
    elementData: [
      {
        cellData: {
          status: "bijlage",
          zaakId: "Bouwtekening.pdf",
          behandelaar: "Openbaar",
          resultaat: "23 maart 2020",
        }
      },
      {
        cellData: {
          status: "bijlage",
          zaakId: "Bouwtekening.pdf",
          behandelaar: "Openbaar",
          resultaat: "23 maart 2020",
        }
      },
    ]
  }
  constructor() { }

  ngOnInit(): void {
  }

}
