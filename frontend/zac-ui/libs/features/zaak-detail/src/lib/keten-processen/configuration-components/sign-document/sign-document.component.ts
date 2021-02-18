import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { TaskContextData } from '../../../../models/task-context';
import { FormArray, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { ApplicationHttpClient } from '@gu/services';
import { KetenProcessenService } from '../../keten-processen.service';
import { atleastOneValidator } from '@gu/utils';
import { Result } from '../../../../models/user-search';

@Component({
  selector: 'gu-sign-document',
  templateUrl: './sign-document.component.html',
  styleUrls: ['../configuration-components.scss']
})
export class SignDocumentComponent implements OnChanges {
  @Input() taskContextData: TaskContextData;

  steps = 1;
  minDate = new Date();
  items: Result[] = [];

  // Form
  signDocumentForm: FormGroup;

  constructor(
    private http: ApplicationHttpClient,
    private fb: FormBuilder,
    private ketenProcessenService: KetenProcessenService,
  ) { }

  ngOnChanges(changes: SimpleChanges) {
    if (changes.taskContextData.previousValue !== this.taskContextData ) {
      this.signDocumentForm = this.fb.group({
        documents: this.addDocumentCheckboxes(),
        assignedUsers: this.fb.array([this.addAssignUsersStep()]),
      }, Validators.required)
    }
  }

  addStep() {
    this.steps++
    this.assignedUsers.push(this.addAssignUsersStep());
  }

  deleteStep(index) {
    this.steps--
    document.querySelector(`#configuration-select--${index}`).remove();
    this.assignedUsers.removeAt(this.assignedUsers.length - 1);
  }

  addDocumentCheckboxes() {
    const arr = this.taskContextData.context.documents.map(() => {
      return this.fb.control(false);
    });
    return this.fb.array(arr, atleastOneValidator());
  }

  addAssignUsersStep() {
    const formGroup = this.fb.group({
      username: this.fb.control("", Validators.minLength(1)),
      firstName: this.fb.control(""),
      lastName: this.fb.control(""),
      email: this.fb.control("", Validators.email),
    })
    return this.fb.control(formGroup);
  }

  get documents(): FormArray {
    return this.signDocumentForm.controls.documents as FormArray;
  };

  get assignedUsers(): FormArray {
    return this.signDocumentForm.controls.assignedUsers as FormArray;
  };

  onSearch(searchInput) {
    this.ketenProcessenService.getAccounts(searchInput).subscribe(res => {
      this.items = res.results;
    })
  }

  submitForm() {
    const selectedDocuments = this.documents.value
      .map((checked, i) => checked ? this.taskContextData.context.documents[i].url : null)
      .filter(v => v !== null);
    const assignedUsers = this.assignedUsers.controls
      .map( step => {
        return {
          username: step.value.controls['username'].value,
          firstName: step.value.controls['firstName'].value,
          lastName: step.value.controls['lastName'].value,
          email: step.value.controls['email'].value
        }
      })
    const formData = {
      form: this.taskContextData.form,
      assignedUsers: assignedUsers,
      selectedDocuments: selectedDocuments,
    };
    this.putForm(formData);
  }

  putForm(formData) {
    this.ketenProcessenService.putTaskData(this.taskContextData.task.id, formData).subscribe(() => {
    })
  }
}
