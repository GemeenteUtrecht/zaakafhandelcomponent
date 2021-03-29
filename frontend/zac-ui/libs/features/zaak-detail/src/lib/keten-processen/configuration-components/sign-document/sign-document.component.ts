import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges } from '@angular/core';
import { TaskContextData } from '../../../../models/task-context';
import { FormArray, FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
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

  @Output() successReload: EventEmitter<boolean> = new EventEmitter<boolean>();

  steps = 1;
  minDate = new Date();
  items: Result[] = [];

  signDocumentForm: FormGroup;

  isSubmitting: boolean;
  submitSuccess: boolean;
  submitHasError: boolean;
  submitErrorMessage: string;

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
      })
    }
  }

  addStep() {
    this.steps++
    this.assignedUsers.push(this.addAssignUsersStep());
  }

  deleteStep() {
    this.steps--
    this.assignedUsers.removeAt(this.assignedUsers.length - 1);
  }

  onSearch(searchInput) {
    this.ketenProcessenService.getAccounts(searchInput).subscribe(res => {
      this.items = res.results.map(result => ({
        ...result,
        name: (result.firstName && result.lastName) ?
          `${result.firstName} ${result.lastName}` :
          (result.firstName && !result.lastName) ?
            result.firstName : result.username
      }))
    })
  }

  submitForm() {
    const selectedDocuments = this.documents.value
      .map((checked, i) => checked ? this.taskContextData.context.documents[i].url : null)
      .filter(v => v !== null);
    const assignedUsers = this.assignedUsers.controls
      .map( (step, i) => {
        return {
          username: this.assignedUsersUsername(i).value,
          firstName: this.assignedUsersFirstname(i).value,
          lastName: this.assignedUsersLastname(i).value,
          email: this.assignedUsersEmail(i).value
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
      this.isSubmitting = false;
      this.submitSuccess = true;
      this.successReload.emit(true);
    }, res => {
      this.isSubmitting = false;
      this.submitErrorMessage = res.error.detail ? res.error.detail : "Er is een fout opgetreden";
      this.submitHasError = true;
    })
  }

  addDocumentCheckboxes() {
    const arr = this.taskContextData.context.documents.map(() => {
      return this.fb.control(false);
    });
    return this.fb.array(arr, atleastOneValidator());
  }

  addAssignUsersStep() {
    return this.fb.group({
      username: ["", Validators.minLength(1)],
      firstName: [""],
      lastName: [""],
      email: ["", {validators: Validators.email, updateOn: 'blur'}],
    })
  }

  get documents(): FormArray {
    return this.signDocumentForm.get('documents') as FormArray;
  };

  get assignedUsers(): FormArray {
    return this.signDocumentForm.get('assignedUsers')  as FormArray;
  };

  assignedUsersUsername(index: number): FormControl {
    return this.assignedUsers.at(index).get('username') as FormControl;
  }

  assignedUsersFirstname(index: number): FormControl {
    return this.assignedUsers.at(index).get('firstName') as FormControl;
  }

  assignedUsersLastname(index: number): FormControl {
    return this.assignedUsers.at(index).get('lastName') as FormControl;
  }

  assignedUsersEmail(index: number): FormControl {
    return this.assignedUsers.at(index).get('email') as FormControl;
  }
}
