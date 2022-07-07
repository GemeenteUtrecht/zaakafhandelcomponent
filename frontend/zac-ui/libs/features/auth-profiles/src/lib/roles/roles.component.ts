import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {FeaturesAuthProfilesService} from '../features-auth-profiles.service';
import {FieldConfiguration, ModalService, SnackbarService} from '@gu/components';
import {Role} from '@gu/models';
import {HttpErrorResponse} from '@angular/common/http';


/**
 * This component displays all the existing roles
 * and allows the user to create new roles.
 *
 * A role is a set of permissions.
 */
@Component({
  selector: 'gu-roles',
  templateUrl: './roles.component.html',
  styleUrls: ['./roles.component.scss']
})
export class RolesComponent implements OnInit {
  @Input() roles: Role[];
  @Output() reloadRoles: EventEmitter<boolean> = new EventEmitter<boolean>();

  /** @type {Role} The role currently being edited. */
  role: Role | null = null;

  /** @type {*} The permissions. */
  permissions: any;

  /** @type {boolean} Whether the API is loading. */
  isLoading: boolean;

  /** @type {string} The error message. */
  errorMessage: string;

  readonly createRoleSuccessMessage = "De rol is aangemaakt."
  readonly createRoleErrorMessage = "Er is een fout opgetreden bij het aanmaken van de rol."

  readonly updateRoleSuccessMessage = "De rol is bijgewerkt."
  readonly updateRoleErrorMessage = "Er is een fout opgetreden bij het bijwerken van de rol."

  readonly deleteRoleSuccessMessage = "De rol is verwijderd."
  readonly deleteRoleErrorMessage = "Er is een fout opgetreden bij het verwijderen van de rol."


  /**
   * Constructor method.
   * @param fService
   * @param modalService
   * @param snackbarService
   */
  constructor(
    private fService: FeaturesAuthProfilesService,
    private modalService: ModalService,
    private snackbarService: SnackbarService
  ) {
  }

  //
  // Getters / setters.
  //

  /**
   * Form for creating a role.
   * @returns {FieldConfiguration[]}
   */
  get form(): FieldConfiguration[] {
    const value = this.role?.permissions || []

    return [
      {
        label: 'Rolnaam',
        name: 'name',
        required: true,
        autocomplete: 'off',
        value: this.role?.name || '',
      },
      {
        choices: this.permissions.map(permission => {
          return {
            label: permission.name,
            value: permission.name
          }
        }),
        multiple: true,
        label: '',
        name: 'permissions',
        required: true,
        value: value,
        widgetType: 'checkboxGroup',
      },
    ];
  }

  //
  // Angular lifecycle.
  //

  ngOnInit(): void {
    this.getPermissions();
  }

  //
  // Context.
  //

  /**
   * Retrieve permissions.
   */
  getPermissions() {
    this.fService.getPermissions().subscribe(
      (data) => this.permissions = data,
      (err) => console.error(err),
    );
  }

  //
  // Events.
  //

  /**
   * Gets called when the add role button is clicked.
   */
  onAddRoleClick() {
    this.role = null;
    this.modalService.open('add-role-modal');
  }

  /**
   * Gets called when an edit role button is clicked.
   */
  onEditRoleClick(role: Role) {
    this.role = role;
    this.modalService.open('add-role-modal');
  }

  /**
   * Gets called when the form is submitted.
   * @param data
   */
  formSubmit(data) {
    if(this.role) {
      return this.updateRole(data)
    }
    return this.createRole(data)
  }

  /**
   * Creates a role.
   * @param data
   */
  createRole(data) {
    this.isLoading = true;
    this.fService.createRole(data).subscribe(
      () => {
        this.modalService.close('add-role-modal');
        this.snackbarService.openSnackBar(this.createRoleSuccessMessage, 'Sluiten', 'primary');
        this.reloadRoles.emit(true);
        this.isLoading = false;
      },
      (err: HttpErrorResponse) => {
        this.errorMessage = this.createRoleErrorMessage;
        this.reportError(err)
      }
    )
  }

  /**
   * Updates role
   * @param data
   */
  updateRole(data) {
    this.isLoading = true;
    this.fService.updateRole(this.role, data).subscribe(
      () => {
        this.modalService.close('add-role-modal');
        this.snackbarService.openSnackBar(this.updateRoleSuccessMessage, 'Sluiten', 'primary');
        this.reloadRoles.emit(true);
        this.isLoading = false;
      },
      (err: HttpErrorResponse) => {
        this.errorMessage = this.updateRoleErrorMessage;
        this.reportError(err)
      }
    )
  }

  /**
   * Deletes role.
   * @param {Role} role
   */
  deleteRole(role: Role) {
    this.isLoading = true;
    this.fService.deleteRole(role).subscribe(
      () => {
        this.snackbarService.openSnackBar(this.deleteRoleSuccessMessage, 'Sluiten', 'primary');
        this.reloadRoles.emit(true);
        this.isLoading = false;
      },
      (err: HttpErrorResponse) => {
        this.errorMessage = this.deleteRoleErrorMessage;
        this.reportError(err)
      }
    )
  }

  //
  // Error handling.
  //

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    this.snackbarService.openSnackBar(error?.error?.name || this.errorMessage, 'Sluiten', 'warn');
    console.error(error);
    this.isLoading = false;
  }
}
