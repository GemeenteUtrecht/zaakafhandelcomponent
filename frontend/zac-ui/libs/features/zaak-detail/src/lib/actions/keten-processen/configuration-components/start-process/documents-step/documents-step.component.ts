import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { Zaak } from '@gu/models';
import { BenodigdeBijlage, TaskContextData } from '../../../../../../models/task-context';
import { FormArray, FormBuilder, FormControl } from '@angular/forms';
import { AccountsService, ZaakService } from '@gu/services';
import { SnackbarService } from '@gu/components';

@Component({
  selector: 'gu-documents-step',
  templateUrl: './documents-step.component.html',
  styleUrls: ['../start-process.component.scss']
})
export class DocumentsStepComponent implements OnChanges {

  @Input() zaak: Zaak;
  @Input() taskContextData: TaskContextData;

  startProcessDocumentForm: any;
  errorMessage: string;

  submittedDocuments: number[] = [];
  submittingDocuments: number[] = [];

  constructor(
    private fb: FormBuilder,
    private zaakService: ZaakService,
    private accountsService: AccountsService,
    private snackbarService: SnackbarService,
  ) { }

  //
  // Getters / setters.
  //

  get documentsControl(): FormArray {
    return this.startProcessDocumentForm.get('documents') as FormArray;
  };

  documentControl(i): FormControl {
    return this.documentsControl.at(i) as FormControl;
  }

  //
  // Angular lifecycle.
  //

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.taskContextData.previousValue !== this.taskContextData ) {
      this.startProcessDocumentForm = this.fb.group({
        documents: this.addDocumentControls()
      })
      this.submittedDocuments = [];
      this.submittingDocuments = [];
    }
  }

  //
  // Context.
  //

  getDocumentsContext(i): BenodigdeBijlage {
    return this.taskContextData.context.benodigdeBijlagen[i];
  }

  addDocumentControls(): FormArray {
    const arr = this.taskContextData.context.benodigdeBijlagen.map(() => {
      return this.fb.control('');
    });
    return this.fb.array(arr);
  }

  isSubmittedDocument(i) {
    return this.submittedDocuments.indexOf(i) !== -1;
  }

  //
  // Events
  //

  async handleFileSelect(file: File, i: number) {
    this.documentControl(i).setValue(file)
  }

  submitDocument(i) {
    const selectedDocument = this.getDocumentsContext(i);
    this.submittingDocuments.push(i)
    this.documentControl(i).disable()

    const newCaseDocument = new FormData();

    newCaseDocument.append("file", this.documentControl(i).value);
    newCaseDocument.append("informatieobjecttype", selectedDocument.informatieobjecttype.url);
    newCaseDocument.append("zaak", this.zaak.url);

    this.zaakService.createCaseDocument(newCaseDocument)
      .subscribe(() => {
        this.submittingDocuments = this.submittingDocuments.filter(index => index !== i);
        this.submittedDocuments.push(i);
      }, error => {
        this.submittingDocuments = this.submittingDocuments.filter(index => index !== i);
        this.documentControl(i).enable();
        this.errorMessage = 'Het aanmaken van de eigenschap is mislukt.'
        this.reportError(error)
      })
  }

  //
  // Error handling.
  //

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    this.snackbarService.openSnackBar(this.errorMessage, 'Sluiten', 'warn');
    console.error(error);
  }
}
