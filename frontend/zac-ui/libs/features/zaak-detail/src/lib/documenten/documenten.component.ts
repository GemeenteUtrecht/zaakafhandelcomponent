import { Component, HostListener, Input, OnChanges } from '@angular/core';
import {Document, ReadWriteDocument, Table } from '@gu/models';
import {DocumentenService, ZaakService} from '@gu/services';
import { ModalService, SnackbarService } from '@gu/components';
import { catchError, switchMap } from 'rxjs/operators';
import { of } from 'rxjs';

/**
 * <gu-documenten [mainZaakUrl]="mainZaakUrl" [bronorganisatie]="bronorganisatie" [identificatie]="identificatie"></gu-documenten>
 *
 * This section displays the documents for a zaak and allow to add documents.
 *
 * Requires mainZaakUrl: string input to identify the url of the case (zaak).
 * Requires zaaktypeurl: string input to identify the url of the case (zaak) type.
 * Requires bronorganisatie: string input to identify the organisation.
 * Requires identificatie: string input to identify the case (zaak).
 */
@Component({
  selector: 'gu-documenten',
  templateUrl: './documenten.component.html',
  styleUrls: ['./documenten.component.scss']
})

export class DocumentenComponent implements OnChanges {
  @Input() mainZaakUrl: string;
  @Input() zaaktypeurl: string;
  @Input() bronorganisatie: string;
  @Input() identificatie: string;

  readonly alertText = "U heeft uw documenten niet opgeslagen. Klik op 'Bewerkingen opslaan' in de documenten sectie om uw wijzigingen op te slaan."
  readonly errorMessage = "Er is een fout opgetreden bij het laden van de documenten.";

  tableHead = [
    '',
    'Bestandsnaam',
    'Versie',
    'Acties',
    '',
    '',
    'Auteur',
    'Type',
  ]

  tableData: Table = new Table(this.tableHead, []);

  isLoading = true;

  documentsData: any;

  selectedDocument: Document;
  selectedDocumentUrl: string;

  constructor(
    private documentenService: DocumentenService,
    private modalService: ModalService,
    private zaakService: ZaakService,
    private snackbarService: SnackbarService
  ) { }

  ngOnChanges(): void {
    this.fetchDocuments()
  }

  /**
   * Show an alert if the user refreshes or closes the browser without saving the edited documents.
   * Only fires if the user has had activity on the documents component.
   * @param $event
   */
  @HostListener('window:beforeunload', ['$event'])
  warnDocsInEditMode($event) {
    // Check if there are any documents in edit mode
    const hasOpenDoc = this.documentsData?.some((doc: Document) => doc.currentUserIsEditing);
    if (hasOpenDoc) {
      this.snackbarService.openSnackBar(this.alertText, 'Sluiten', 'warn', 10);
      $event.preventDefault();
      $event.returnValue = this.alertText;
    }
  }

  /**
   * Fetch all the documents related to the case.
   */
  fetchDocuments() {
    this.isLoading = true;

    this.zaakService.listCaseDocuments(this.bronorganisatie, this.identificatie).subscribe( data => {
      this.tableData = this.documentenService.formatTableData(data, this.tableHead);
      this.documentsData = data;

      this.isLoading = false;
    }, res => {
      const message = res.error.detail || this.errorMessage;
      this.snackbarService.openSnackBar(message, "Sluiten", 'warn')
      this.isLoading = false;
    })
  }

  /**
   * Chains the button action to the matching function
   * @param {object} action
   */
  handleTableButtonOutput(action: object) {
    const actionType = Object.keys(action)[0];
    const actionUrl = action[actionType];

    switch (actionType) {
      case 'bestandsnaam':
        this.patchDocumentName(actionUrl);
        break;
      case 'lezen':
        this.readDocument(actionUrl);
        break;
      case 'bewerken':
        this.editDocument(actionUrl);
        break;
      case 'overschrijven':
        this.patchDocument(actionUrl);
        break;
    }
  }

  /**
   * Opens the document in another browser or application.
   * @param readUrl
   */
  readDocument(readUrl) {
    this.isLoading = true;
    this.documentenService.readDocument(readUrl).subscribe( (res: ReadWriteDocument) => {
      this.isLoading = false;

      // Check if Microsoft Office application file
      if (res.magicUrl.substr(0,3) === "ms-") {
        window.open(res.magicUrl, "_self");
      } else {
        window.open(res.magicUrl, "_blank");
      }
    }, () => {
      this.snackbarService.openSnackBar(this.errorMessage, "Sluiten", 'warn')
      this.isLoading = false;
    })
  }

  /**
   * Opens the selected document in edit mode or closes the edit mode.
   * A user is only allowed to edit one file at a time.
   * @param writeUrl
   */
  editDocument(writeUrl) {
    const selectedDoc: Document = this.documentsData.find((doc: Document) => doc.writeUrl === writeUrl);
    const hasOpenDoc = this.documentsData.some((doc: Document) => doc.currentUserIsEditing);

    // Open the document if the current user is not already editing it and has no other files open.
    if (!selectedDoc.currentUserIsEditing && !hasOpenDoc) {
      this.openDocumentEdit(writeUrl);
      // Show message if the user is already editing another document.
    } else if (!selectedDoc.currentUserIsEditing && hasOpenDoc) {
      const message = "U kunt maar één document tegelijk bewerken."
      this.snackbarService.openSnackBar(message, "Sluiten")
      // Exit edit mode
    } else {
      this.closeDocumentEdit(writeUrl);
    }
  }

  /**
   * Opens the "gu-document-toevoegen" component
   * @param documentUrl
   */
  patchDocument(documentUrl) {
    this.selectedDocumentUrl = documentUrl;
    this.openModal('document-overschrijven-modal')
  }

  /**
   * Opens the "gu-bestandseigenschappen-wijzigen-modal" component
   * @param document
   */
  patchDocumentName(document) {
    this.selectedDocument = document;
    this.openModal('bestandseigenschappen-wijzigen-modal')
  }

  /**
   * Fetches the document url to open the document.
   * @param writeUrl
   */
  openDocumentEdit(writeUrl) {
    this.isLoading = true;
    this.documentenService.openDocumentEdit(writeUrl).subscribe( (res: ReadWriteDocument) => {

      // Check if Microsoft Office application file
      if (res.magicUrl.substr(0,3) === "ms-") {
        window.open(res.magicUrl, "_self");
      } else {
        window.open(res.magicUrl, "_blank");
      }

      // Refresh table layout so "Bewerkingen opslaan" button will be shown
      this.fetchDocuments();
    }, () => {
      this.snackbarService.openSnackBar(this.errorMessage, "Sluiten", 'warn')
      this.isLoading = false;
    })
  }

  /**
   * Save edited documents.
   * @param writeUrl
   */
  closeDocumentEdit(writeUrl) {
    this.isLoading = true;
    // Retrieve the deleteUrl of the selected document. This url is required to close the edit mode.
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
        // Refresh section
        this.fetchDocuments();
      }, () => {
        this.snackbarService.openSnackBar(this.errorMessage, "Sluiten", 'warn')
        this.isLoading = false;
      })
  }

  /**
   * Open a modal.
   * @param {string} id
   */
  openModal(id: string) {
    this.modalService.open(id);
  }

  /**
   * Close a modal.
   * @param {string} id
   */
  closeModal(id: string) {
    this.modalService.close(id);
  }
}
