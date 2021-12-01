import { Component, OnInit } from '@angular/core';
import { FeaturesAuthProfilesService } from '../features-auth-profiles.service';
import { UserGroupResult } from '../../../../zaak-detail/src/models/user-group-search';
import { ModalService, SnackbarService } from '@gu/components';
import { UserGroupDetail } from '@gu/models';

@Component({
  selector: 'gu-user-groups',
  templateUrl: './user-groups.component.html',
  styleUrls: ['./user-groups.component.scss']
})
export class UserGroupsComponent implements OnInit {

  isLoading: boolean;
  isDetailsLoading: boolean;
  errorMessage: string;

  userGroupsList: UserGroupResult[];
  userGroupsDetails: UserGroupDetail[] = [];

  selectedEditModeGroup: UserGroupDetail;
  selectedDeleteModeGroup: UserGroupDetail;

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

  fetchUserGroupDetails(groupList: UserGroupResult[]) {
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
