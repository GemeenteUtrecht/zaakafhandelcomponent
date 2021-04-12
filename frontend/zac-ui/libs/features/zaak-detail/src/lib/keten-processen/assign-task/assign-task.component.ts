import { Component, EventEmitter, Input, OnChanges, Output } from '@angular/core';
import { FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { Observable } from 'rxjs';
import { Result, UserSearch } from '../../../models/user-search';
import { ApplicationHttpClient } from '@gu/services';
import { Task } from '../../../models/keten-processen'

@Component({
  selector: 'gu-assign-task',
  templateUrl: './assign-task.component.html',
  styleUrls: ['./assign-task.component.scss']
})
export class AssignTaskComponent implements OnChanges {
  @Input() currentUser: string;
  @Input() taskData: Task;
  @Output() reload: EventEmitter<boolean> = new EventEmitter<boolean>();

  assignTaskForm: FormGroup;

  users: Result[] = [];

  isSubmitting: boolean;
  submitHasError: boolean;
  submitErrorMessage: string;
  submitSuccess: boolean;

  constructor(
    private http: ApplicationHttpClient,
    private fb: FormBuilder
  ) { }

  ngOnChanges(): void {
    this.submitSuccess = false;
    this.submitHasError = false;
    this.isSubmitting = false;

    if (this.taskData) {
      this.assignTaskForm = this.fb.group({
        task: this.taskData.id,
        assignee: this.fb.control("", Validators.required)
      })
    }
  }

  get task(): FormControl {
    return this.assignTaskForm.get('task') as FormControl;
  };

  get assignee(): FormControl {
    return this.assignTaskForm.get('assignee') as FormControl;
  };


  onSearch(searchInput) {
    this.getAccounts(searchInput).subscribe(res => {
      this.users = res.results.map(result => ({
        ...result,
        name: (result.firstName && result.lastName) ?
          `${result.firstName} ${result.lastName}` :
          (result.firstName && !result.lastName) ?
            result.firstName : result.username
      }))
    })
  }

  submitForm() {
    this.isSubmitting = true;
    const formData = {
      task: this.task.value,
      assignee: this.assignee.value,
      delegate: ""
    }

    this.postAssignTask(formData).subscribe( () => {
      this.submitSuccess = true;
      this.submitHasError = false;
      this.isSubmitting = false;
      this.reload.emit(true)
    }, error => {
      this.submitHasError = true;
      this.submitErrorMessage =
        error?.error?.detail ? error.error.detail
          : error?.error?.nonFieldErrors ? error.error?.nonFieldErrors[0]
          : 'Er is een fout opgetreden'
      this.isSubmitting = false;
    })
  }

  getAccounts(searchInput: string): Observable<UserSearch>{
    const endpoint = encodeURI(`/api/accounts/users?search=${searchInput}`);
    return this.http.Get<UserSearch>(endpoint);
  }

  postAssignTask(formData) {
    const endpoint = encodeURI('/api/camunda/claim-task');
    return this.http.Post<any>(endpoint, formData)
  }

}
