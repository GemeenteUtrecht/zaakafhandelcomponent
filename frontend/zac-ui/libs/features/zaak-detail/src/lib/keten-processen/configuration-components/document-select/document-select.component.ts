import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges } from '@angular/core';
import { TaskContextData } from '../../../../models/task-context';
import { FormArray, FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { ApplicationHttpClient } from '@gu/services';
import { KetenProcessenService } from '../../keten-processen.service';
import { atleastOneValidator } from '@gu/utils';
import { ReadWriteDocument } from '../../../documenten/documenten.interface';

@Component({
  selector: 'gu-document-select',
  templateUrl: './document-select.component.html',
  styleUrls: ['../configuration-components.scss']
})
export class DocumentSelectComponent implements OnChanges {
  @Input() taskContextData: TaskContextData;

  @Output() successReload: EventEmitter<boolean> = new EventEmitter<boolean>();

  selectDocumentsForm: FormGroup

  isSubmitting: boolean;
  submitSuccess: boolean;
  submitHasError: boolean;
  submitErrorMessage: string;

  openSelectorsArray: number[] = [];

  constructor(
    private http: ApplicationHttpClient,
    private fb: FormBuilder,
    private ketenProcessenService: KetenProcessenService,
  ) { }

  ngOnChanges(changes: SimpleChanges): void {
    this.selectDocumentsForm = this.fb.group({
      documents: this.addDocumentCheckboxes(),
      documentTypes: this.addDocumentTypes()
    }, Validators.required)
    if (changes.taskContextData.previousValue !== this.taskContextData ) {
      this.selectDocumentsForm = this.fb.group({
        documents: this.addDocumentCheckboxes(),
        documentTypes: this.addDocumentTypes()
      }, Validators.required)
    }
  }

  addDocumentCheckboxes() {
    const arr = this.taskContextData.context.documents.map(() => {
      return this.fb.control(false);
    });
    return this.fb.array(arr, atleastOneValidator());
  }

  addDocumentTypes() {
    const arr = this.taskContextData.context.documents.map(() => {
      return this.fb.control('');
    });
    return this.fb.array(arr);
  }

  get documents(): FormArray {
    return this.selectDocumentsForm.get('documents') as FormArray;
  };

  get documentTypes(): FormArray {
    return this.selectDocumentsForm.get('documentTypes') as FormArray;
  };

  documentType(index: number): FormControl {
    return this.documentTypes.at(index) as FormControl;
  }

  submitForm() {
    this.isSubmitting = true;
    const selectedDocuments = this.documents.value
      .map((checked, i) => checked ? {
        document: this.taskContextData.context.documents[i].url,
        documentType: this.documentType(i).value ? this.getDocumentTypeUrl(this.documentType(i).value) : this.getDocumentTypeUrl(this.taskContextData.context.documents[i].documentType)
      } : null)
      .filter(v => v !== null);
    const formData = {
      form: this.taskContextData.form,
      selectedDocuments: selectedDocuments,
    };
    this.putForm(formData);
  }

  putForm(formData) {
    this.ketenProcessenService.putTaskData(this.taskContextData.task.id, formData).subscribe(() => {
      this.isSubmitting = false;
      this.submitSuccess = true;
      this.successReload.emit(true);
    }, res => {
      this.isSubmitting = false;
      this.submitErrorMessage = res.error.detail ? res.error.detail : "Er is een fout opgetreden";
      this.submitHasError = true;
    })
  }

  readDocument(url) {
    this.ketenProcessenService.readDocument(url).subscribe((res: ReadWriteDocument) => {
      window.open(res.magicUrl, "_blank");
    });
  }

  openDocumentTypeSelector(i: number) {
    this.openSelectorsArray.push(i);
  }

  closeDocumentTypeSelector(i: number) {
    const index = this.openSelectorsArray.indexOf(i);
    if (index !== -1) {
      this.openSelectorsArray.splice(index, 1);
    }
    this.documentType(i).patchValue(null)
  }

  getDocumentTypeUrl(documentType) {
    const documentTypeObject = this.taskContextData.context.informatieobjecttypen
      .filter(type => {
        return type.omschrijving === documentType;
      })[0]
    return documentTypeObject.url;
  }

}
