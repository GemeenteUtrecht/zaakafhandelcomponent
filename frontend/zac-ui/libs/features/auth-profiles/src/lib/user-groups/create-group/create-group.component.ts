import { Component, EventEmitter, Input, OnChanges, OnInit, Output } from '@angular/core';
import { UntypedFormBuilder, UntypedFormControl, UntypedFormGroup, Validators } from '@angular/forms';
import { MatCheckboxChange } from '@angular/material/checkbox';
import { FeaturesAuthProfilesService } from '../../features-auth-profiles.service';
import { ModalService, SnackbarService } from '@gu/components';
import { UserGroupDetail, UserSearchResult } from '@gu/models';

/**
 * Allows user to create or edit a user group.
 */
@Component({
  selector: 'gu-create-group',
  templateUrl: './create-group.component.html',
  styleUrls: ['./create-group.component.scss']
})
export class CreateGroupComponent implements OnChanges {
  @Input() type: "create" | "edit";
  @Input() selectedUserGroup: UserGroupDetail;
  @Output() reloadGroups: EventEmitter<any> = new EventEmitter<any>();

  isSubmitting: boolean;
  errorMessage: string;

  newUserGroupForm: UntypedFormGroup;
  currentSearchValue: string;

  searchResultUsers: UserSearchResult[];

  selectedUsers: UserSearchResult[] = [];

  readonly createGroupSuccessMessage = "De gebruikersgroep is aangemaakt."
  readonly createGroupErrorMessage = "Er is een fout opgetreden bij het aanmaken van de gebruikersgroep."
  readonly editGroupSuccessMessage = "De gebruikersgroep is gewijzigd."
  readonly editGroupErrorMessage = "Er is een fout opgetreden bij het wijzigen van de gebruikersgroep."

  constructor(
    private fService: FeaturesAuthProfilesService,
    private modalService: ModalService,
    private snackbarService: SnackbarService,
    private fb: UntypedFormBuilder,
  ) {
    this.newUserGroupForm = this.fb.group({
      name: this.fb.control("", Validators.required),
      searchValue: this.fb.control(""),
      checkboxControl: this.fb.control(""),
    })
  }

  //
  // Getters / setters.
  //

  get userGroupNameControl(): UntypedFormControl {
    return this.newUserGroupForm.get('name') as UntypedFormControl;
  };

  get checkboxControl(): UntypedFormControl {
    return this.newUserGroupForm.get('checkboxControl') as UntypedFormControl;
  };


  get searchValueControl(): UntypedFormControl {
    return this.newUserGroupForm.get('searchValue') as UntypedFormControl;
  }

  //
  // Angular lifecycle.
  //

  /**
   * A lifecycle hook that is called when any data-bound property of a directive changes. Define an ngOnChanges() method
   * to handle the changes.
   */
  ngOnChanges(): void {
    this.searchUsers();
    if (this.type === "edit" && this.selectedUserGroup) {
      this.setContextEditMode();
    }
  }

  //
  // Context.
  //

  /**
   * Set data for edit mode.
   */
  setContextEditMode() {
    this.userGroupNameControl.patchValue(this.selectedUserGroup.name);
    this.selectedUsers = this.selectedUserGroup.users;
  }

  /**
   * Search accounts.
   */
  searchUsers() {
    if (this.searchValueControl.value !== this.currentSearchValue) {
      this.currentSearchValue = this.searchValueControl.value;
      if (this.currentSearchValue) {
        this.fService.getAccounts(this.currentSearchValue).subscribe(res => {
          this.searchResultUsers = res.results;
        }, error => {
          this.reportError(error)
        })
      }
    }
  }

  /**
   * Submits user group data.
   * @param {"create" | "edit"} type
   */
  submitUserGroup(type: "create" | "edit") {
    this.isSubmitting = true;
    const formData = {
      "name": this.userGroupNameControl.value,
      "users": this.selectedUsers.map(userObj => userObj.username),
    }

    if ( type === "create") {
      this.fService.createUserGroup(formData).subscribe( () => {
        this.snackbarService.openSnackBar(this.createGroupSuccessMessage, 'Sluiten', 'primary')
        this.resetForm();
      }, error => {
        this.errorMessage = this.createGroupErrorMessage;
        this.reportError(error)
      })
    }

    if ( type === "edit") {
      this.fService.updateUserGroup(formData, this.selectedUserGroup.id).subscribe( () => {
        this.snackbarService.openSnackBar(this.editGroupSuccessMessage, 'Sluiten', 'primary')
        this.resetForm();
      }, error => {
        this.errorMessage = this.editGroupErrorMessage;
        this.reportError(error)
      })
    }
  }

  /**
   * Resets form.
   */
  resetForm() {
    this.isSubmitting = false;
    if (this.type === 'create') {
      this.newUserGroupForm.reset();
    }
    this.selectedUsers = [];
    this.reloadGroups.emit(true);
    this.modalService.close('add-usergroup-modal')
  }

  /**
   * Update selected users array.
   * @param {MatCheckboxChange} event
   */
  updateSelectedUsers(event: MatCheckboxChange) {
    const selectedValue: UserSearchResult = Object(event.source.value);
    const isInSelectedUsers = this.isInSelectedUser(selectedValue);
    if (event.checked && !isInSelectedUsers) {
      this.selectedUsers.push(selectedValue)
    } else if (!event.checked && isInSelectedUsers) {
      const i = this.selectedUsers.findIndex(userObj => userObj.id === selectedValue.id);
      this.selectedUsers.splice(i, 1);
    }
  }

  /**
   * Check if user exists in current selected users array.
   * @param {UserSearchResult} user
   * @returns {boolean}
   */
  isInSelectedUser(user: UserSearchResult) {
    return this.selectedUsers.some(userObj => userObj.id === user.id);
  }

  /**
   * Convert selected users to human readible string.
   * @returns {string[]}
   */
  showSelectedUsers() {
    return this.selectedUsers.map(userObj => ' ' + (userObj.fullName || userObj.username)).sort();
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
    this.isSubmitting = false;
  }

}
