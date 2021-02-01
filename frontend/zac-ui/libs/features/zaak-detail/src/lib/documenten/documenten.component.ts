import { Component, OnInit } from '@angular/core';
import { CellData, Table, RowData } from '@gu/models';
import { ApplicationHttpClient } from '@gu/services';
import { ActivatedRoute } from '@angular/router';
import { Observable } from 'rxjs';
import { HttpResponse } from '@angular/common/http';
import { convertKbToMb } from '@gu/utils';

import { Document, DocumentUrls, ReadWriteDocument } from './documenten.interface';
import { DocumentenService } from './documenten.service';

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

  documentsData: any;

  isLoading = true;
  hasError: boolean;
  errorMessage: string;

  bronorganisatie: string;
  identificatie: string;

  docsInEditMode: string[] = [];
  deleteUrls: DocumentUrls[] = [];

  constructor(
    private http: ApplicationHttpClient,
    private route: ActivatedRoute,
    private documentenService: DocumentenService
  ) {
    this.route.paramMap.subscribe( params => {
      this.bronorganisatie = params.get('bronorganisatie');
      this.identificatie = params.get('identificatie');
    });
  }

  ngOnInit(): void {
    this.isLoading = true;
    this.documentenService.getDocuments(this.bronorganisatie, this.identificatie).subscribe( data => {
      this.tableData.bodyData = this.formatTableData(data)
      this.documentsData = data;
      this.isLoading = false;
    }, res => {
      this.errorMessage = res.error.detail;
      this.hasError = true;
      this.isLoading = false;
    })
  }

  formatTableData(data): RowData[] {
    return data.map( (element: Document) => {
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

    switch (actionType) {
      case 'lezen':
        this.readDocument(actionUrl);
        break;
      case 'bewerken':
        this.editDocument(actionUrl);
        break;
    }
    if (actionType === 'bewerken') {
      this.editDocument(actionUrl);
    }
  }

  readDocument(readUrl) {
    this.documentenService.readDocument(readUrl).subscribe( (res: ReadWriteDocument) => {
      window.open(res.magicUrl, "_blank");
    }, errorResponse => {

    })
  }

  editDocument(writeUrl) {
    if (!this.docsInEditMode.includes(writeUrl)) {
      this.docsInEditMode.push(writeUrl);
      this.openDocumentEdit(writeUrl);
    } else {
      this.deleteUrls.forEach( (document, index) => {
        if (document.writeUrl === writeUrl) {
          this.closeDocumentEdit(document.deleteUrl, writeUrl);
          this.deleteUrls.splice(index, 1);
        }
      })
    }
  }

  openDocumentEdit(writeUrl) {
    this.documentenService.openDocumentEdit(writeUrl).subscribe( (res: ReadWriteDocument) => {
      // Open document
      window.open(res.magicUrl, "_blank");

      // Change table layout so "Bewerkingen opslaan" button will be shown
      this.tableData.bodyData = this.formatTableData(this.documentsData);

      // Map received deleteUrl to the writeUrl
      this.addDeleteUrlsMapping(writeUrl, res.deleteUrl);
    }, errorResponse => {

    })
  }

  closeDocumentEdit(deleteUrl, writeUrl) {
    return this.documentenService.closeDocumentEdit(deleteUrl).subscribe( res => {
      // Remove deleteUrl mapping from local array
      this.deleteUrls.forEach( (document, index) => {
        if (document.deleteUrl === deleteUrl) {
          this.deleteUrls.splice(index, 1);
        }
      })

      // Remove editMode
      this.docsInEditMode = this.docsInEditMode.filter(e => e !== writeUrl);
      this.tableData.bodyData = this.formatTableData(this.documentsData);
    }, errorResponse => {

    })
  }

  addDeleteUrlsMapping(writeUrl, deleteUrl) {
    const urlMapping = {
      writeUrl: writeUrl,
      deleteUrl: deleteUrl
    }
    this.deleteUrls.push(urlMapping);
  }

}
