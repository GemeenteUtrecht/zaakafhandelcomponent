import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { TaskContextData } from '../../../../models/task-context';
import { FormArray, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { ApplicationHttpClient } from '@gu/services';
import { KetenProcessenService } from '../../keten-processen.service';
import { atleastOneValidator } from '@gu/utils';

@Component({
  selector: 'gu-document-select',
  templateUrl: './document-select.component.html',
  styleUrls: ['../configuration-components.scss']
})
export class DocumentSelectComponent implements OnChanges {
  @Input() taskContextData: TaskContextData;

  selectDocumentsForm: FormGroup

  constructor(
    private http: ApplicationHttpClient,
    private fb: FormBuilder,
    private ketenProcessenService: KetenProcessenService,
  ) { }

  ngOnChanges(changes: SimpleChanges): void {
    this.selectDocumentsForm = this.fb.group({
      documents: this.addDocumentCheckboxes()
    }, Validators.required)
    if (changes.taskContextData.previousValue !== this.taskContextData ) {
      this.selectDocumentsForm = this.fb.group({
        documents: this.addDocumentCheckboxes()
      }, Validators.required)
    }
  }

  addDocumentCheckboxes() {
    const arr = this.taskContextData.context.documents.map(() => {
      return this.fb.control(false);
    });
    return this.fb.array(arr, atleastOneValidator());
  }

  get documents(): FormArray {
    return this.selectDocumentsForm.controls.documents as FormArray;
  };

  submitForm() {
    const selectedDocuments = this.documents.value
      .map((checked, i) => checked ? this.taskContextData.context.documents[i].url : null)
      .filter(v => v !== null);
    const formData = {
      form: this.taskContextData.form,
      selectedDocuments: selectedDocuments,
    };
    this.putForm(formData);
  }

  putForm(formData) {
    this.ketenProcessenService.putTaskData(this.taskContextData.task.id, formData).subscribe(() => {
    })
  }

}
