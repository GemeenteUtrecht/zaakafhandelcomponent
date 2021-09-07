import { Component, OnInit } from '@angular/core';
import { FeaturesAuthProfilesService } from '../features-auth-profiles.service';
import { ModalService, SnackbarService } from '@gu/components';
import { AuthProfile, MetaZaaktype, Result, Role } from '@gu/models';


/**
 * Displays authentication profiles.
 */
@Component({
  selector: 'gu-auth-profiles',
  templateUrl: './auth-profiles.component.html',
  styleUrls: ['./auth-profiles.component.scss']
})
export class AuthProfilesComponent implements OnInit {

  readonly getAuthProfilesErrorMessage = "Er is een fout opgetreden bij het ophalen van de autorisatieprofielen.";
  readonly getRolesErrorMessage = "Er is een fout opgetreden bij het ophalen van de rollen.";

  roles: Role[];
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
    this.getRoles();
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
   * Convert case id to omschrijving.
   * @param id
   * @returns {string}
   */
  getCaseTypeName(id) {
    const caseTypeObj = this.caseTypes.results.find(caseType => caseType.identificatie === id)
    return caseTypeObj.omschrijving
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
   * Retrieve roles.
   */
  getRoles() {
    this.isLoading = true;
    this.fService.getRoles().subscribe(
      (data) => this.roles = data,
      (err) => {
        this.errorMessage = this.getRolesErrorMessage;
        this.reportError(err)
      }
    );
    this.isLoading = false;
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
