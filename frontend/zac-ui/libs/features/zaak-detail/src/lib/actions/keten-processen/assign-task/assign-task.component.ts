import { Component, EventEmitter, Input, OnChanges, Output } from '@angular/core';
import { UntypedFormBuilder, UntypedFormControl, UntypedFormGroup, Validators } from '@angular/forms';
import { SnackbarService } from '@gu/components';
import {Task, User, UserGroupDetail, UserSearchResult} from '@gu/models';
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

  assignUserForm: UntypedFormGroup;
  assignUserGroupForm: UntypedFormGroup;

  users: UserSearchResult[] = [];
  userGroups: UserGroupDetail[] = [];

  isSubmitting: boolean;
  errorMessage: string;
  submitSuccess: boolean;

  showForm: boolean;

  constructor(
    private kService: KetenProcessenService,
    private fb: UntypedFormBuilder,
    private snackbarService: SnackbarService
  ) { }

  //
  // Getters / setters.
  //

  get assigneeUserControl(): UntypedFormControl {
    return this.assignUserForm.get('assignee') as UntypedFormControl;
  };

  get assigneeUserGroupControl(): UntypedFormControl {
    return this.assignUserGroupForm.get('assignee') as UntypedFormControl;
  };

  //
  // Angular lifecycle.
  //

  /**
   * Respond when Angular sets or resets data-bound input properties.
   */
  ngOnChanges(): void {
    this.submitSuccess = false;
    this.isSubmitting = false;

    if (this.taskData) {
      this.assignUserForm = this.fb.group({
        assignee: this.fb.control("", Validators.required)
      })

      this.assignUserGroupForm = this.fb.group({
        assignee: this.fb.control("", Validators.required)
      })

      this.showForm = this.kService.isUserAllowedToAssignTask(this.currentUser, this.taskData)
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
      this.isSubmitting = false;
      this.successReload.emit(true)
    }, error => {
      this.reportError(error)
      this.isSubmitting = false;
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
    this.errorMessage =
      error?.error?.detail ? error.error.detail
        : error?.error?.nonFieldErrors ? error.error?.nonFieldErrors[0]
        : 'Er is een fout opgetreden'
    this.snackbarService.openSnackBar(this.errorMessage, 'Sluiten', 'warn');
    console.error(error);
  }
}
