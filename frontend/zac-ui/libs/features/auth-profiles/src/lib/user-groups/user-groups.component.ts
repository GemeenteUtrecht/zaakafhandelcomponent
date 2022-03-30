import { Component, OnInit } from '@angular/core';
import { FeaturesAuthProfilesService } from '../features-auth-profiles.service';
import { ModalService, SnackbarService } from '@gu/components';
import { UserGroupDetail, UserSearchResult } from '@gu/models';

/**
 * Managing component for user groups.
 */
@Component({
  selector: 'gu-user-groups',
  templateUrl: './user-groups.component.html',
  styleUrls: ['./user-groups.component.scss']
})
export class UserGroupsComponent implements OnInit {

  isLoading: boolean;
  isDetailsLoading: boolean;
  errorMessage: string;

  userGroupsList: UserGroupDetail[];
  userGroupsDetails: UserGroupDetail[] = [];

  selectedEditModeGroup: UserGroupDetail;
  selectedDeleteModeGroup: UserGroupDetail;

  allUsers: UserSearchResult[];

  constructor(
    private fService: FeaturesAuthProfilesService,
    private modalService: ModalService,
    private snackbarService: SnackbarService,
  ) {
  }

  //
  // Angular lifecycle.
  //

  /**
   * A lifecycle hook that is called after Angular has initialized all data-bound properties of a directive. Define an
   * ngOnInit() method to handle any additional initialization tasks.
   */
  ngOnInit(): void {
    this.getAllUsers();
    this.listUserGroups();
  }

  //
  // Context.
  //

  /**
   * Opens modal
   * @param id
   */
  openModal(id) {
    this.modalService.open(id);
  }

  /**
   * Closes modal.
   * @param id
   */
  closeModal(id) {
    this.modalService.close(id);
  }

  /**
   * Returns full name if present.
   * @param {string} username
   * @returns {string}
   */
  getFullName(username: string) {
    const user = this.allUsers.find(userDetail => userDetail.username === username);
    return user.fullName ? user.fullName : user.username;
  }

  /**
   * Show array of pretty names instead of usernames
   * @param {string[]} users
   * @returns {string[]}
   */
  prettifyUsers(users: string[]) {
    return users.map(user => this.getFullName(user)).sort();
  }

  /**
   * Get all user accounts.
   */
  getAllUsers() {
    this.fService.getAccounts('').subscribe(res => {
      this.allUsers = res.results;
    }, error => {
      this.reportError(error)
    })
  }

  /**
   * Open modal to edit user group.
   * @param {UserGroupDetail} group
   */
  editUserGroup(group: UserGroupDetail) {
    this.selectedEditModeGroup = group;
    this.openModal('edit-usergroup-modal');
  }

  /**
   * Open modal to delete user group.
   * @param {UserGroupDetail} group
   */
  deleteUserGroup(group: UserGroupDetail) {
    this.selectedDeleteModeGroup = group;
    this.openModal('delete-usergroup-modal');
  }

  /**
   * Retrieve user groups.
   */
  listUserGroups() {
    this.isLoading = true;
    this.fService.listUserGroups().subscribe(
      (data) => {
        this.userGroupsList = data.results;
        this.fetchUserGroupDetails(data.results)
        this.isLoading = false;
      },
      (err) => {
        this.isLoading = false;
        this.errorMessage = "Fout bij het ophalen van de groepen.";
        this.reportError(err);
      }
    );
  }

  /**
   * Retrieve details per user group.
   * @param {UserGroupDetail[]} groupList
   */
  fetchUserGroupDetails(groupList: UserGroupDetail[]) {
    this.userGroupsDetails = [];
    this.isDetailsLoading = true;
    this.fService.getUserGroupDetailsBatch(groupList).subscribe((userGroupDetail) => {
      userGroupDetail.map(detail => {
        this.userGroupsDetails.push(detail);
      })
      this.isDetailsLoading = false;
    }, error => {
      this.isDetailsLoading = false;
      this.reportError(error);
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
    this.isLoading = false;
  }

}
