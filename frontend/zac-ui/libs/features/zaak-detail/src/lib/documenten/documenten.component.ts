import { Component, Input, OnChanges } from '@angular/core';
import {Document, DocumentUrls, ReadWriteDocument, Table, RowData, ExtensiveCell} from '@gu/models';
import {ApplicationHttpClient, ZaakService} from '@gu/services';
import { DocumentenService } from './documenten.service';
import { ModalService } from '@gu/components';

@Component({
  selector: 'gu-documenten',
  templateUrl: './documenten.component.html',
  styleUrls: ['./documenten.component.scss']
})

export class DocumentenComponent implements OnChanges {
  @Input() mainZaakUrl: string;
  @Input() bronorganisatie: string;
  @Input() identificatie: string;

  tableData: Table = new Table([
    '',
    'Bestandsnaam',
    'Versie',
    'Acties',
    '',
    '',
    'Type',
    'Vertrouwelijkheid',
  ], []);

  documentsData: any;

  isLoading = true;
  hasError: boolean;
  errorMessage: string;

  docsInEditMode: string[] = [];
  deleteUrls: DocumentUrls[] = [];

  selectedDocument: Document;
  selectedDocumentUrl: string;

  constructor(
    private http: ApplicationHttpClient,
    private documentenService: DocumentenService,
    private modalService: ModalService,
    private zaakService: ZaakService,
  ) { }

  ngOnChanges(): void {
    this.fetchDocuments()
  }

  fetchDocuments() {
    this.isLoading = true;
    this.zaakService.listCaseDocuments(this.bronorganisatie, this.identificatie).subscribe( data => {
      this.tableData.bodyData = this.formatTableData(data);
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
     const iconInfo = element.locked ? 'Het document wordt al door een ander persoon bewerkt.' : 'U kunt het document bewerken. Klik op "Bewerkingen opslaan" na het bewerken.'
     const editLabel = this.docsInEditMode.includes(element.writeUrl) ? 'Bewerkingen opslaan' : 'Bewerken';
     const editButtonStyle = this.docsInEditMode.includes(element.writeUrl) ? 'primary' : 'tertiary';
     const showEditCell = !element.locked || this.docsInEditMode.includes(element.writeUrl);
     const editCell: ExtensiveCell = {
       type: 'button',
       label: editLabel,
       value: element.writeUrl,
       buttonType: editButtonStyle
     };
     const overwriteCell: ExtensiveCell = {
        type: 'button',
        label: 'Overschrijven',
        value: element.url
      };
     const confidentialityButton: ExtensiveCell | string = element.locked ? element.vertrouwelijkheidaanduiding : {
       type: 'button',
       label: element.vertrouwelijkheidaanduiding,
       value: element
     }

     const cellData: RowData = {
       cellData: {
         opSlot: {
           type: 'icon',
           label: icon,
           iconColor: iconColor,
           iconInfo: iconInfo
         },
         bestandsnaam: element.bestandsnaam,
         versie: String(element.versie),
         lezen: {
           type: 'button',
           label: 'Lezen',
           value: element.readUrl
         },
         bewerken: showEditCell ? editCell : '',
         overschrijven:  element.locked ? '' : overwriteCell,
         type: element.informatieobjecttype['omschrijving'],
         vertrouwelijkheid: confidentialityButton
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
      case 'overschrijven':
        this.patchDocument(actionUrl);
        break;
      case 'vertrouwelijkheid':
        this.patchConfidentiality(actionUrl);
        break;
    }
    if (actionType === 'bewerken') {
      this.editDocument(actionUrl);
    }
  }

  readDocument(readUrl) {
    this.isLoading = true;
    this.documentenService.readDocument(readUrl).subscribe( (res: ReadWriteDocument) => {
      this.isLoading = false;
      window.open(res.magicUrl, "_blank");
    }, errorResponse => {
      this.isLoading = false;
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

  patchDocument(documentUrl) {
    this.selectedDocumentUrl = documentUrl;
    this.openModal('document-overschrijven-modal')
  }

  patchConfidentiality(document: Document) {
    this.selectedDocument = document;
    this.openModal('document-vertrouwelijkheid-wijzigen-modal')
  }

  openDocumentEdit(writeUrl) {
    this.isLoading = true;
    this.documentenService.openDocumentEdit(writeUrl).subscribe( (res: ReadWriteDocument) => {
      // Open document
      window.open(res.magicUrl, "_blank");

      // Change table layout so "Bewerkingen opslaan" button will be shown
      this.fetchDocuments();

      // Map received deleteUrl to the writeUrl
      this.addDeleteUrlsMapping(writeUrl, res.deleteUrl);

      this.isLoading = false;
    }, errorResponse => {
      this.isLoading = false;
    })
  }

  closeDocumentEdit(deleteUrl, writeUrl) {
    this.isLoading = true;
    return this.documentenService.closeDocumentEdit(deleteUrl).subscribe( res => {
      // Remove deleteUrl mapping from local array
      this.deleteUrls.forEach( (document, index) => {
        if (document.deleteUrl === deleteUrl) {
          this.deleteUrls.splice(index, 1);
        }
      })

      // Remove editMode
      this.docsInEditMode = this.docsInEditMode.filter(e => e !== writeUrl);
      this.fetchDocuments();

      this.isLoading = false;
    }, errorResponse => {
      this.isLoading = false;
    })
  }

  addDeleteUrlsMapping(writeUrl, deleteUrl) {
    const urlMapping = {
      writeUrl: writeUrl,
      deleteUrl: deleteUrl
    }
    this.deleteUrls.push(urlMapping);
  }

  openModal(id: string) {
    this.modalService.open(id);
  }

  closeModal(id: string) {
    this.modalService.close(id);
  }
}
