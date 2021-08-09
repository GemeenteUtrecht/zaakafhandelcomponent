import { Component, Host, HostListener, Input, OnChanges } from '@angular/core';
import {Document, DocumentUrls, ReadWriteDocument, Table, RowData, ExtensiveCell} from '@gu/models';
import {ApplicationHttpClient, ZaakService} from '@gu/services';
import { DocumentenService } from './documenten.service';
import { ModalService, SnackbarService } from '@gu/components';
import { catchError, switchMap } from 'rxjs/operators';
import { of } from 'rxjs';

@Component({
  selector: 'gu-documenten',
  templateUrl: './documenten.component.html',
  styleUrls: ['./documenten.component.scss']
})

export class DocumentenComponent implements OnChanges {
  @Input() mainZaakUrl: string;
  @Input() bronorganisatie: string;
  @Input() identificatie: string;

  tableHead = [
    '',
    'Bestandsnaam',
    'Versie',
    'Acties',
    '',
    '',
    'Type',
    'Vertrouwelijkheid',
  ]

  alertText = "U heeft uw documenten niet opgeslagen. Klik op 'Bewerkingen opslaan' in de documenten sectie om uw wijzigingen op te slaan."

  tableData: Table = new Table(this.tableHead, []);

  documentsData: any;

  isLoading = true;
  errorMessage = "Er is een fout opgetreden bij het laden van de documenten.";

  docsInEditMode: string[] = [];
  deleteUrls: DocumentUrls[] = [];

  selectedDocument: Document;
  selectedDocumentUrl: string;

  constructor(
    private http: ApplicationHttpClient,
    private documentenService: DocumentenService,
    private modalService: ModalService,
    private zaakService: ZaakService,
    private snackbarService: SnackbarService
  ) { }

  ngOnChanges(): void {
    this.fetchDocuments()
  }

  @HostListener('window:beforeunload', ['$event'])
  async warnDocsInEditMode($event) {
    const hasOpenDoc = this.documentsData?.some((doc: Document) => doc.currentUserIsEditing);
    if (hasOpenDoc) {
      await this.snackbarService.openSnackBar(this.alertText, 'Sluiten', 'warn', 10);
      $event.preventDefault();
      $event.returnValue = this.alertText;
    }
  }

  fetchDocuments() {
    this.isLoading = true;

    this.zaakService.listCaseDocuments(this.bronorganisatie, this.identificatie).subscribe( data => {
      this.tableData = this.formatTableData(data);
      this.documentsData = data;

      this.isLoading = false;
    }, res => {
      const message = res.error.detail || this.errorMessage;
      this.snackbarService.openSnackBar(message, "Sluiten", 'warn')
      this.isLoading = false;
    })
  }

  formatTableData(data): Table {
    const tableData: Table = new Table(this.tableHead, []);

    tableData.bodyData = data.map( (element: Document) => {
     const icon = (element.locked && !element.currentUserIsEditing) ? 'lock' : 'lock_open'
     const iconColor = (element.locked && !element.currentUserIsEditing) ? 'orange' : 'green'
     const iconInfo = (element.locked && !element.currentUserIsEditing) ? 'Het document wordt al door een ander persoon bewerkt.' : 'U kunt het document bewerken. Klik op "Bewerkingen opslaan" na het bewerken.'
     const editLabel = element.currentUserIsEditing ? 'Bewerkingen opslaan' : 'Bewerken';
     const editButtonStyle = element.currentUserIsEditing  ? 'primary' : 'tertiary';
     const showEditCell = !element.locked || element.currentUserIsEditing;
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

    return tableData
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
  }

  readDocument(readUrl) {
    this.isLoading = true;
    this.documentenService.readDocument(readUrl).subscribe( (res: ReadWriteDocument) => {
      this.isLoading = false;
      window.open(res.magicUrl, "_blank");
    }, () => {
      this.snackbarService.openSnackBar(this.errorMessage, "Sluiten", 'warn')
      this.isLoading = false;
    })
  }

  editDocument(writeUrl) {
    const selectedDoc: Document = this.documentsData.find((doc: Document) => doc.writeUrl === writeUrl);
    const hasOpenDoc = this.documentsData.some((doc: Document) => doc.currentUserIsEditing);
    if (!selectedDoc.currentUserIsEditing && !hasOpenDoc) {
      this.openDocumentEdit(writeUrl);
    } else if (!selectedDoc.currentUserIsEditing && hasOpenDoc) {
      const message = "U kunt maar één document tegelijk bewerken."
      this.snackbarService.openSnackBar(message, "Sluiten")
    } else {
      this.closeDocumentEdit(writeUrl);
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
    }, () => {
      this.snackbarService.openSnackBar(this.errorMessage, "Sluiten", 'warn')
      this.isLoading = false;
    })
  }

  closeDocumentEdit(writeUrl) {
    this.isLoading = true;
    this.documentenService.openDocumentEdit(writeUrl)
      .pipe(
        switchMap((res: ReadWriteDocument) => {
          const { deleteUrl } = res;
          return this.documentenService.closeDocumentEdit(deleteUrl)
        }),
        catchError( () => {
          this.snackbarService.openSnackBar(this.errorMessage, "Sluiten", 'warn')
          this.isLoading = false;
          return of(null)
        })
      )
      .subscribe( () => {
        this.fetchDocuments();
      }, () => {
        this.snackbarService.openSnackBar(this.errorMessage, "Sluiten", 'warn')
        this.isLoading = false;
      })
  }

  openModal(id: string) {
    this.modalService.open(id);
  }

  closeModal(id: string) {
    this.modalService.close(id);
  }
}
