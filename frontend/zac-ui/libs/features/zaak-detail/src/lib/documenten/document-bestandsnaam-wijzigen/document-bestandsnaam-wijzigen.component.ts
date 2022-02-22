import { Component, EventEmitter, Input, Output } from '@angular/core';
import { FieldConfiguration, SnackbarService } from '@gu/components';
import { Document } from '@gu/models';
import { DocumentenService } from '../documenten.service';

/**
 * Component that changes the document name
 *
 * <gu-document-bestandsnaam-wijzigen [mainZaakUrl]="mainZaakUrl"[selectedDocument]="selectedDocument"></gu-document-bestandsnaam-wijzigen>
 */
@Component({
  selector: 'gu-document-bestandsnaam-wijzigen',
  templateUrl: './document-bestandsnaam-wijzigen.component.html',
  styleUrls: ['./document-bestandsnaam-wijzigen.component.scss']
})
export class DocumentBestandsnaamWijzigenComponent {
  @Input() mainZaakUrl: string;
  @Input() selectedDocument: Document;
  @Output() reload: EventEmitter<boolean> = new EventEmitter<boolean>();
  @Output() closeModal: EventEmitter<boolean> = new EventEmitter<boolean>();

  readonly errorMessage = 'Wijzigen bestandsnaam niet gelukt.';

  isLoading: boolean;
  form: FieldConfiguration[] = [
    {
      label: 'Nieuwe bestandsnaam',
      name: 'bestandsnaam',
      required: true,
      autocomplete: 'off',
      value: '',
    },
    {
      label: 'Reden wijziging',
      name: 'reden',
      required: true,
      autocomplete: 'off',
      value: '',
    },
  ];

  constructor(
    private documentService: DocumentenService,
    private snackbarService: SnackbarService,
  ) { }

  /**
   * Submit form data.
   * @param formData
   */
  formSubmit(formData) {
    const data = new FormData();
    data.append('url', this.selectedDocument.url);
    data.append('zaak', this.mainZaakUrl);
    data.append('bestandsnaam', formData.bestandsnaam)
    data.append('reden', formData.reden)

    this.isLoading = true;
    this.documentService.patchDocument(data).subscribe(() => {
      this.reload.emit(true);
      this.closeModal.emit(true);
      this.isLoading = false;
    }, this.reportError.bind(this))
  }


  //
  // Error handling.
  //

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    const submitErrorMessage = error?.error?.nonFieldErrors[0] ? error?.error?.nonFieldErrors[0] : this.errorMessage;
    this.snackbarService.openSnackBar(submitErrorMessage, 'Sluiten', 'warn');
    this.isLoading = false
    console.error(error);
  }
}
