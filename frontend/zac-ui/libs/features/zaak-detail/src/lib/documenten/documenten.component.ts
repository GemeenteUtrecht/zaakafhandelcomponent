import { Component, OnInit } from '@angular/core';
import { CellData, Table, RowData } from '@gu/models';
import { ApplicationHttpClient } from '@gu/services';
import { ActivatedRoute } from '@angular/router';
import { Observable } from 'rxjs';
import { HttpResponse } from '@angular/common/http';
import { convertKbToMb } from '@gu/utils';

import {DocumentUrls } from './documenten.interface';

@Component({
  selector: 'gu-documenten',
  templateUrl: './documenten.component.html',
  styleUrls: ['./documenten.component.scss']
})

export class DocumentenComponent implements OnInit {
  tableData: Table = {
    headData: ['Op slot', 'Acties', '', 'Bestandsnaam', 'Type', 'Vertrouwelijkheid', 'Bestandsgrootte'],
    bodyData: []
  }

  data: any;

  isLoading = true;
  hasError: boolean;
  errorMessage: string;

  bronorganisatie: string;
  identificatie: string;

  docsInEditMode: string[] = [];
  deleteUrls: DocumentUrls[] = [];

  constructor(
    private http: ApplicationHttpClient,
    private route: ActivatedRoute
  ) {
    this.route.paramMap.subscribe( params => {
      this.bronorganisatie = params.get('bronorganisatie');
      this.identificatie = params.get('identificatie');
    });
  }

  ngOnInit(): void {
    this.isLoading = true;
    this.getDocuments().subscribe( data => {
      this.tableData.bodyData = this.formatTableData(data)
      this.data = data;
      this.isLoading = false;
    }, res => {
      this.errorMessage = res.error.detail;
      this.hasError = true;
      this.isLoading = false;
    })
  }

  formatTableData(data): RowData[] {
    return data.map( element => {
     const icon = element.locked ? 'lock' : 'lock_open'
     const iconColor = element.locked ? 'orange' : 'green'
     const bestandsomvang =
       element.bestandsomvang > 999 ? `${(convertKbToMb(element.bestandsomvang, 2)).toLocaleString("nl-NL")} MB`
       : `${element.bestandsomvang} KB`;
     const editLabel = this.docsInEditMode.includes(element.writeUrl) ? 'Bewerkingen opslaan' : 'Bewerken';
     const editButtonStyle = this.docsInEditMode.includes(element.writeUrl) ? 'primary' : 'tertiary';

     const cellData: RowData = {
       cellData: {
         opSlot: {
           type: 'icon',
           label: icon,
           iconColor: iconColor
         },
         lezen: {
           type: 'button',
           label: 'Lezen',
           value: element.readUrl
         },
         bewerken: {
           type: 'button',
           label: editLabel,
           value: element.writeUrl,
           buttonType: editButtonStyle
         },
         bestandsnaam: element.bestandsnaam,
         type: element.informatieobjecttype['omschrijving'],
         vertrouwelijkheid: element.vertrouwelijkheidaanduiding,
         bestandsomvang: bestandsomvang
       }
     }
     return cellData;
    })
  }

  handleTableButtonOutput(action: object) {
    const actionType = Object.keys(action)[0];
    const actionUrl = action[actionType];

    if (actionType === 'bewerken') {
      this.editDocument(actionUrl);
    }
  }

  editDocument(actionUrl) {
    if (!this.docsInEditMode.includes(actionUrl)) {
      this.docsInEditMode.push(actionUrl);
      this.openDocumentEdit(actionUrl);
    } else {
      this.deleteUrls.forEach(document => {
        if (document.actionUrl === actionUrl) {

        }
      })
    }
  }

  openDocumentEdit(actionUrl) {
    this.writeDocuments(actionUrl).subscribe( res => {
      console.log(res);
    }, errorResponse => {

    })
  }

  getDocuments(): Observable<HttpResponse<any>> {
    const endpoint = encodeURI(`/api/core/cases/${this.bronorganisatie}/${this.identificatie}/documents`);
    return this.http.Get<any>(endpoint);
  }

  writeDocuments(writeUrl): Observable<HttpResponse<any>> {
    const endpoint = encodeURI(writeUrl);
    return this.http.Post<any>(endpoint);
  }
}
