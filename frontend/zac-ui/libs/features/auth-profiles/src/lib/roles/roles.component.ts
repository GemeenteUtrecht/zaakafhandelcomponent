import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { FeaturesAuthProfilesService } from '../features-auth-profiles.service';
import { FieldConfiguration, ModalService, SnackbarService } from '@gu/components';
import { Role } from '@gu/models';
import { HttpErrorResponse } from '@angular/common/http';


/**
 * This component allows the user to create a role.
 */
@Component({
  selector: 'gu-roles',
  templateUrl: './roles.component.html',
  styleUrls: ['./roles.component.scss']
})
export class RolesComponent implements OnInit {
  @Input() roles: Role[];
  @Output() reloadRoles: EventEmitter<boolean> = new EventEmitter<boolean>();

  permissions: any;

  isLoading: boolean;

  readonly createRoleSuccessMessage = "De rol is aangemaakt."
  readonly createRoleErrorMessage = "Er is een fout opgetreden bij het aanmaken van de rol."
  errorMessage: string;

  constructor(
    private fService: FeaturesAuthProfilesService,
    private modalService: ModalService,
    private snackbarService: SnackbarService
  ) { }

  ngOnInit(): void {
    this.getPermissions();
  }

  /**
   * Form for creating a role.
   * @returns {FieldConfiguration[]}
   */
  get form(): FieldConfiguration[] {
    return [
      {
        label: 'Rolnaam',
        name: 'name',
        required: true,
        autocomplete: 'off',
        value: '',
      },
      {
        choices: this.permissions.map( permission => {
          return {
            label: `${permission.name}: ${permission.description}`,
            value: permission.name
          }
        }),
        multiple: true,
        label: 'Rechten',
        name: 'permissions',
        required: true,
        value: [],
      },
    ];
  }

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
   * Retrieve permissions.
   */
  getPermissions() {
    this.fService.getPermissions().subscribe(
      (data) => this.permissions = data,
      (err) => console.error(err),
    );
  }

  /**
   * Submit form data.
   * @param data
   */
  formSubmit(data) {
    this.isLoading = true;
    this.fService.createRole(data).subscribe(
      () => {
        this.closeModal('add-role-modal');
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
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    this.snackbarService.openSnackBar(this.errorMessage, 'Sluiten', 'warn');
    console.error(error);
    this.isLoading = false;
  }

}
