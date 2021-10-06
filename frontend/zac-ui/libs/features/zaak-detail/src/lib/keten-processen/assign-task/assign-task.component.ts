import { Component, EventEmitter, Input, OnChanges, Output } from '@angular/core';
import { FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { Result } from '../../../models/user-search';
import { UserGroupResult } from '../../../models/user-group-search';
import { ModalService } from '@gu/components';
import { Task, User } from '@gu/models';
import { KetenProcessenService } from '../keten-processen.service';

/**
 * This component allows tasks to be assigned to a user
 *
 * Requires taskData: Task information
 * Requires currentUser: Logged in user information
 *
 * Emits successReload: Event after finishing submit
 */
@Component({
  selector: 'gu-assign-task',
  templateUrl: './assign-task.component.html',
  styleUrls: ['./assign-task.component.scss']
})
export class AssignTaskComponent implements OnChanges {
  @Input() taskData: Task;
  @Input() currentUser: User;
  @Output() successReload: EventEmitter<boolean> = new EventEmitter<boolean>();

  assignUserForm: FormGroup;
  assignUserGroupForm: FormGroup;

  users: Result[] = [];
  userGroups: UserGroupResult[] = [];

  isSubmitting: boolean;
  submitHasError: boolean;
  submitErrorMessage: string;
  submitSuccess: boolean;

  constructor(
    private kService: KetenProcessenService,
    private fb: FormBuilder,
    private modalService: ModalService
  ) { }

  //
  // Getters / setters.
  //

  get assigneeUserControl(): FormControl {
    return this.assignUserForm.get('assignee') as FormControl;
  };

  get assigneeUserGroupControl(): FormControl {
    return this.assignUserGroupForm.get('assignee') as FormControl;
  };

  //
  // Angular lifecycle.
  //

  /**
   * Respond when Angular sets or resets data-bound input properties.
   */
  ngOnChanges(): void {
    this.submitSuccess = false;
    this.submitHasError = false;
    this.isSubmitting = false;

    if (this.taskData) {
      this.assignUserForm = this.fb.group({
        assignee: this.fb.control("", Validators.required)
      })

      this.assignUserGroupForm = this.fb.group({
        assignee: this.fb.control("", Validators.required)
      })
    }
  }

  //
  // Context.
  //

  /**
   * Search for user accounts.
   * @param searchInput
   */
  onSearchAccounts(searchInput) {
    this.kService.getAccounts(searchInput).subscribe(res => {
      this.users = res.results;
    })
  }

  /**
   * Search for user groups.
   * @param searchInput
   */
  onSearchUserGroups(searchInput) {
    this.kService.getUserGroups(searchInput).subscribe(res => {
      this.userGroups = res.results;
    })
  }

  /**
   * Assign a task to the current user.
   */
  assignSelf() {
    this.assigneeUserControl.patchValue(this.currentUser.username);
    this.submitForm('user');
  }

  /**
   * Submits the form. The form data is dependant on "assignType".
   * @param {"user" | "userGroup"} assignType
   */
  submitForm(assignType: 'user' | 'userGroup') {
    this.isSubmitting = true;
    let assignee;
    switch (assignType) {
      case 'user':
        assignee = this.assigneeUserControl.value;
        break;
      case 'userGroup':
        assignee = this.assigneeUserGroupControl.value;
        break;
    }
    const formData = {
      task: this.taskData.id,
      assignee: assignee,
      delegate: ""
    }

    this.kService.postAssignTask(formData).subscribe(() => {
      this.submitSuccess = true;
      this.submitHasError = false;
      this.isSubmitting = false;
      this.successReload.emit(true)

      this.modalService.close('ketenprocessenModal');
    }, error => {
      this.submitHasError = true;
      this.submitErrorMessage =
        error?.error?.detail ? error.error.detail
          : error?.error?.nonFieldErrors ? error.error?.nonFieldErrors[0]
          : 'Er is een fout opgetreden'
      this.isSubmitting = false;
    })
  }
}
