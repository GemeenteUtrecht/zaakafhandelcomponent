import { Component, HostListener, Input, OnChanges, QueryList, ViewChild, ViewChildren } from '@angular/core';
import { Document, ListDocuments, MetaConfidentiality, ReadWriteDocument, Table, Zaak } from '@gu/models';
import {DocumentenService, MetaService, ZaakService} from '@gu/services';
import { Choice, FieldConfiguration, ModalService, PaginatorComponent, SnackbarService } from '@gu/components';
import {ActivatedRoute, Router} from '@angular/router';
import {Location} from '@angular/common';

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
  @ViewChild(PaginatorComponent) paginator: PaginatorComponent;
  @Input() zaak: Zaak;

  readonly alertText = "U heeft uw documenten niet opgeslagen. Klik op 'Bewerkingen opslaan' in de documenten sectie om uw wijzigingen op te slaan."
  readonly errorMessage = "Er is een fout opgetreden bij het laden van de documenten.";

  tableHead = [
    '',
    'Bestandsnaam',
    'Versie',
    '',
    '',
    '',
    'Auteur',
    'Informatieobjecttype',
    'Vertrouwelijkheidaanduiding',
  ]

  tableData: Table = new Table(this.tableHead, []);
  confidentialityForm: FieldConfiguration[] = [{
    label: "Reden",
    name: "reason",
  }]


  isLoading = true;

  paginatedDocsData: ListDocuments;
  documentsData: any;

  selectedDocument: Document;
  selectedDocumentUrl: string;
  selectedConfidentialityChoice: Choice;

  page = 1;

  sortValue: any;

  constructor(
    private activatedRoute: ActivatedRoute,
    private router: Router,
    private location: Location,
    private documentenService: DocumentenService,
    private metaService: MetaService,
    private modalService: ModalService,
    private zaakService: ZaakService,
    private snackbarService: SnackbarService
  ) {
  }

  ngOnChanges(): void {
    this.fetchDocuments()
  }

  /**
   * Updates the component using a public interface.
   */
  public update() {
    this.fetchDocuments();
  }

  //
  // Context
  //

  refreshDocs() {
    this.isLoading = true;
    this.sortValue = null;
    if (this.paginator) {
      this.paginator.firstPage();
    }
    this.page = 1;
    setTimeout(() => {
      this.fetchDocuments(this.page);
    }, 3000)
  }

  /**
   * Fetch all the documents related to the case.
   */
  fetchDocuments(page = 1, sortValue?) {
    this.isLoading = true;

    this.metaService.listConfidentialityClassifications().subscribe(
      (metaConfidentialities: MetaConfidentiality[]) => {

        this.zaakService.listCaseDocuments(this.zaak.bronorganisatie, this.zaak.identificatie, page, sortValue).subscribe(data => {
          this.tableData = this.documentenService.formatTableData(data.results, this.tableHead, this.zaak, metaConfidentialities, this.onConfidentialityChange.bind(this));
          this.paginatedDocsData = data;
          this.documentsData = data.results;

          this.handleQueryParam();
          this.isLoading = false;
        }, res => {
          const message = res.error.detail || this.errorMessage;
          this.snackbarService.openSnackBar(message, "Sluiten", 'warn')
          this.isLoading = false;
        })
      },
      this.reportError.bind(this)
    )
  }

  /**
   * Open modal according to query param
   */
  handleQueryParam() {
    this.activatedRoute.queryParams.subscribe(queryParams => {
      const modalParam = queryParams['modal'];
      if (modalParam) {
        this.openModal(modalParam);
      }
    });
  }

  /**
   * Opens the document in another browser or application.
   * @param readUrl
   */
  readDocument(readUrl) {
    this.isLoading = true;
    this.documentenService.readDocument(readUrl).subscribe((res: ReadWriteDocument) => {
      this.isLoading = false;

      // Check if Microsoft Office application file
      if (res.magicUrl.substr(0, 3) === "ms-") {
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
   * @param url
   */
  editDocument(url) {
    const selectedDoc: Document = this.documentsData.find((doc: Document) => doc.writeUrl === url || doc.deleteUrl === url);
    const hasOpenDoc = this.documentsData.some((doc: Document) => doc.currentUserIsEditing);

    // Open the document if the current user is not already editing it and has no other files open.
    if (!selectedDoc.currentUserIsEditing && !hasOpenDoc) {
      this.openDocumentEdit(url);
      // Show message if the user is already editing another document.
    } else if (!selectedDoc.currentUserIsEditing && hasOpenDoc) {
      const message = "U kunt maar één document tegelijk bewerken."
      this.snackbarService.openSnackBar(message, "Sluiten", "accent")
      // Exit edit mode
    } else {
      this.closeDocumentEdit(url);
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
    this.documentenService.openDocumentEdit(writeUrl, this.zaak.url).subscribe((res: ReadWriteDocument) => {

      // Check if Microsoft Office application file
      if (res.magicUrl.substr(0, 3) === "ms-") {
        window.open(res.magicUrl, "_self");
      } else {
        window.open(res.magicUrl, "_blank");
      }

      // Refresh table layout so "Bewerkingen opslaan" button will be shown
      this.fetchDocuments();
    }, error => {
      this.reportError(error);
      this.isLoading = false;
    })
  }

  /**
   * Save edited documents.
   * @param deleteUrl
   */
  closeDocumentEdit(deleteUrl) {
    this.isLoading = true;
    this.documentenService.closeDocumentEdit(deleteUrl).subscribe(() => {
      // Refresh section
      this.refreshDocs();
    }, () => {
      this.snackbarService.openSnackBar(this.errorMessage, "Sluiten", 'warn')
      this.isLoading = false;
    })
  }

  //
  // Events.
  //

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
   * Removes all query params
   */
  removeQueryParam() {
    this.selectedDocument = null;
    this.router.navigate(
      [],
      {
        relativeTo: this.activatedRoute,
        queryParams: {modal: null, tab: null},
        queryParamsHandling: 'merge'
      }
    );
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
   * Open a modal.
   * @param {string} id
   */
  openModal(id: string) {
    this.modalService.open(id);
    this.router.navigate(
      [],
      {
        relativeTo: this.activatedRoute,
        queryParams: {modal: id},
        queryParamsHandling: 'merge'
      }
    );
  }

  /**
   * Close a modal.
   * @param {string} id
   */
  closeModal(id: string) {
    this.modalService.close(id);
  }

  onConfidentialityChange(document: Document, confidentialityChoice: Choice) {
    this.selectedDocument = document;
    this.selectedConfidentialityChoice = confidentialityChoice;
    setTimeout(() => {
      this.openModal("document-confidentiality-modal");
    })
  }

  /**
   * Gets called when this.confidentialityForm is submitted.
   * @param {Object} data
   */
  onConfidentialitySubmit(data) {
    this.isLoading = true;

    const choiceValue = this.selectedConfidentialityChoice.value as "openbaar" | "beperkt_openbaar" | "intern" | "zaakvertrouwelijk" | "vertrouwelijk" | "confidentieel" | "geheim" | "zeer_geheim"
    this.documentenService.setConfidentiality(this.selectedDocument.url, choiceValue, data.reason, this.zaak.url).subscribe(
      () => this.closeModal("document-confidentiality-modal"),
      () => this.reportError.bind(this),
      () => this.isLoading =false,
    );
    this.refreshDocs();
  }

  /**
   * When paginator fires
   * @param uuid
   * @param page
   */
  onPageSelect(page) {
    this.page = page.pageIndex + 1;
    this.fetchDocuments(this.page, this.sortValue);
  }

  sortTable(sortValue) {
    this.paginator.firstPage();
    this.page = 1;
    this.sortValue = sortValue;
    this.fetchDocuments(this.page, this.sortValue);
  }

  //
  // Error handling.
  //

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    const message = error?.error?.detail || error?.error[0]?.reason || error?.error.nonFieldErrors?.join(', ') || this.errorMessage;
    this.snackbarService.openSnackBar(message, 'Sluiten', 'warn');
    console.error(error);
    this.isLoading = false;
  }
}
