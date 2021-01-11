import { Component, OnInit } from '@angular/core';
import { Table } from '@gu/models';

@Component({
  selector: 'gu-adviseren-accorderen',
  templateUrl: './adviseren-accorderen.component.html',
  styleUrls: ['./adviseren-accorderen.component.scss']
})
export class AdviserenAccorderenComponent implements OnInit {
  tableData: Table = {
    headData: ['Type', 'Opgehaald'],
    tableData: [
      {
        cellData: {
          type: "Advies",
          opgehaald: "0/1",
        }
      },
      {
        cellData: {
          type: "Advies",
          opgehaald: "0/2",
        }
      },
    ]
  }
  constructor() { }

  ngOnInit(): void {
  }

}
