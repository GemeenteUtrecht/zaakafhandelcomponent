import { Component, EventEmitter, Input, OnChanges, Output } from '@angular/core';
import { FieldConfiguration, SnackbarService } from '@gu/components';
import { Document } from '@gu/models';
import { DocumentenService } from '../documenten.service';

/**
 * Component that changes the document name
 *
 * <gu-document-wijzigen [mainZaakUrl]="mainZaakUrl"[selectedDocument]="selectedDocument"></gu-document-wijzigen>
 */
@Component({
  selector: 'gu-document-wijzigen',
  templateUrl: './document-wijzigen.component.html',
  styleUrls: ['./document-wijzigen.component.scss']
})
export class DocumentWijzigenComponent {
  @Input() mainZaakUrl: string;
  @Input() selectedDocument: Document;

  @Output() reload: EventEmitter<boolean> = new EventEmitter<boolean>();
  @Output() closeModal: EventEmitter<boolean> = new EventEmitter<boolean>();

  readonly errorMessage = 'Wijzigen bestandsnaam niet gelukt.';

  isLoading: boolean;

  constructor(
    private documentService: DocumentenService,
    private snackbarService: SnackbarService,
  ) { }

  get form(): FieldConfiguration[] {
    return [
      {
        label: 'Bestandsnaam',
        placeholder: ' ',
        name: 'bestandsnaam',
        required: true,
        autocomplete: 'off',
        value: this.selectedDocument.titel.split('.').slice(0, -1).join('.'),
      },
      {
        label: 'Beschrijving',
        placeholder: '-',
        name: 'beschrijving',
        autocomplete: 'off',
        required: true,
        value: this.selectedDocument.beschrijving,
      },
      {
        label: 'Reden wijziging',
        name: 'reden',
        value: '',
        required: true,
        writeonly: true,
      },
      {
        label: 'Auteur',
        name: 'auteur',
        value: this.selectedDocument.auteur,
        readonly: true,
      },
      {
        label: 'Documenttype',
        name: 'documenttype',
        value: this.selectedDocument.titel.split('.').pop(),
        readonly: true,
      },
      {
        label: 'Vertrouwelijkheid',
        name: 'vertrouwelijkheid',
        value: this.selectedDocument.vertrouwelijkheidaanduiding,
        readonly: true,
      },
      {
        label: 'Versie',
        name: 'versie',
        value: this.selectedDocument.versie,
        readonly: true,
      },
      {
        label: 'Bestandsomvang',
        name: 'bestandsomvang',
        value: `${this.selectedDocument.bestandsomvang}kb`,
        readonly: true,
      },
    ];
  }

  /**
   * Submit form data.
   * @param formData
   */
  formSubmit(formData) {
    const data = new FormData();
    data.append('url', this.selectedDocument.url);
    data.append('zaak', this.mainZaakUrl);
    if (formData.bestandsnaam) {
      data.append('bestandsnaam', formData.bestandsnaam)
    }
    if (formData.beschrijving) {
      data.append('beschrijving', formData.beschrijving)
    }
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
