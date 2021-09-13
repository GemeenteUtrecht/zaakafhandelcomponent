import { Component, Input, OnInit } from '@angular/core';
import { FeaturesAuthProfilesService } from '../features-auth-profiles.service';
import { ModalService, SnackbarService } from '@gu/components';
import { AuthProfile, MetaZaaktype, Result, Role } from '@gu/models';


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

  /**
   * Retrieve auth profiles.
   */
  getAuthProfiles() {
    this.isLoading = true;
    this.fService.getAuthProfiles().subscribe(
      (data) => {
        this.isLoading = false;
        this.authProfiles = data},
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
