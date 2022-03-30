import { Component, Input, OnInit } from '@angular/core';
import { FeaturesAuthProfilesService } from '../features-auth-profiles.service';
import { ModalService, SnackbarService } from '@gu/components';
import { AuthProfile, MetaZaaktype, Role, UserAuthProfile, UserAuthProfiles } from '@gu/models';

/**
 * Displays the retrieved authorisation profiles with its roles and policies.
 * Only authorisation profiles with at least one object type "zaak" will be shown.
 */
@Component({
  selector: 'gu-auth-profiles',
  templateUrl: './auth-profiles.component.html',
  styleUrls: ['./auth-profiles.component.scss']
})
export class AuthProfilesComponent implements OnInit {
  @Input() roles: Role[];

  readonly getAuthProfilesErrorMessage = "Er is een fout opgetreden bij het ophalen van de autorisatieprofielen.";

  authProfiles: AuthProfile[];
  selectedAuthProfile: AuthProfile;
  selectedUserAuthProfiles: UserAuthProfile[];
  userAuthProfiles: UserAuthProfile[];
  caseTypes: MetaZaaktype;

  isLoading: boolean;
  errorMessage: string;

  constructor(
    private fService: FeaturesAuthProfilesService,
    private modalService: ModalService,
    private snackbarService: SnackbarService
  ) { }

  ngOnInit(): void {
    this.getAuthProfiles();
    this.getUserAuthProfiles();
    this.getCaseTypes();
  }

  /**
   * Opens modal.
   * @param id
   */
  openModal(id) {
    this.modalService.open(id)
  }

  /**
   * Closes the modal.
   * @param id
   */
  closeModal(id) {
    this.modalService.close(id);
  }


  /**
   * Open modal to edit auth profile.
   * @param authProfile
   * @param userAuthProfiles
   */
  editAuthProfile(authProfile: AuthProfile, userAuthProfiles: UserAuthProfile[]) {
    this.selectedAuthProfile = authProfile;
    this.selectedUserAuthProfiles = userAuthProfiles;
    this.openModal('edit-auth-profile-modal');
  }

  /**
   * Open modal to delete auth profile.
   * @param {AuthProfile} authProfile
   */
  deleteAuthProfile(authProfile: AuthProfile) {
    this.selectedAuthProfile = authProfile;
    this.openModal('delete-auth-profile-modal');
  }

  /**
   * Convert role id to name.
   * @param id
   * @returns {string}
   */
  getRoleName(id) {
    const roleObj: Role = this.roles.find(role => role.id === id);
    return roleObj.name;
  }

  /**
   * Check if authorisation profile has at least one object type "zaak" in it.
   * @param {AuthProfile} authProfile
   * @returns {boolean}
   */
  showAuthProfile(authProfile: AuthProfile) {
    return authProfile.blueprintPermissions.some(perm => perm.objectType === "zaak")
  }

  filterUserAuthProfiles(uuid) {
    return this.userAuthProfiles.filter((profile) => profile.authProfile.uuid === uuid)
      .sort((a,b) => ((a.user.fullName || a.user.username) > (b.user.fullName || b.user.username)) ? 1 : (((b.user.fullName || b.user.username) > (a.user.fullName || a.user.username)) ? -1 : 0));
  }

  filterUserAuthProfileUsers(uuid) {
    const profiles = this.filterUserAuthProfiles(uuid);
    return profiles.map((profile) => profile.user);
  }

  /**
   * Retrieve auth profiles.
   */
  getAuthProfiles() {
    this.selectedAuthProfile = null;
    this.isLoading = true;
    this.fService.getAuthProfiles().subscribe(
      (data) => {
        this.isLoading = false;
        this.authProfiles = data
      },
      (err) => {
        this.isLoading = false;
        this.errorMessage = this.getAuthProfilesErrorMessage;
        this.reportError(err);
      }
    );
  }

  /**
   * Retrieve auth profiles.
   */
  getUserAuthProfiles() {
    this.isLoading = true;
    this.fService.getUserAuthProfiles().subscribe(
      (data: UserAuthProfiles) => {
        this.isLoading = false;
        this.userAuthProfiles = data.results;
      },
      (err) => {
        this.isLoading = false;
        this.errorMessage = this.getAuthProfilesErrorMessage;
        this.reportError(err);
      }
    );
  }

  /**
   * Fetches zaaktypen.
   */
  getCaseTypes() {
    this.fService.getCaseTypes().subscribe(
      (data) => this.caseTypes = data,
      (error) => console.error(error),
    );
  }

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
