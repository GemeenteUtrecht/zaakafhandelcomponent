import {Component, Input, OnInit} from '@angular/core';
import { ZaakPermission, UserPermission, Table, Zaak, WorkstackAdvice, RowData, ExtensiveCell } from '@gu/models';
import {ZaakService} from "@gu/services";
import {PermissionsService} from './permissions.service';
import {ModalService, SnackbarService} from '@gu/components';

/**
 * <gu-user-permissions [bronorganisatie]="bronorganisatie" [identificatie]="identificatie"></gu-user-permissions>
 *
 * Show user permissions for bronorganisatie/identificatie.
 *
 * Requires bronorganisatie: string input to identify the organisation.
 * Requires identificatie: string input to identify the case (zaak).
 */
@Component({
  providers: [PermissionsService],
  selector: 'gu-user-permissions',
  styleUrls: ['./user-permissions.component.scss'],
  templateUrl: './user-permissions.component.html',
})
export class UserPermissionsComponent implements OnInit {
  @Input() zaak: Zaak;

  /** @type {string} Error message. */
  readonly errorMessage = 'Er is een fout opgetreden bij het laden van gebruikersrechten.'

  /** @type {string} Error message. */
  errorDetailMessage = '';

  /** @type {boolean} Whether this component is loading. */
  isLoading = false;

  /** @type {ZaakPermission} The selected (for removal) permission. */
  selectedPermission: ZaakPermission = null;

  /** @type {Table} The Table to render. */
  table: Table = null;

  /** @type {Table} The short version of Table to render. */
  shortTable: Table = null;

  /** @type {UserPermission[]} The user permissions. */
  userPermissions: UserPermission[];
  shortUserPermissions: UserPermission[];

  /** @type {boolean} Wether table rows are all shown */
  isExpanded = false;

  constructor(
    private permissionsService: PermissionsService,
    private modalService: ModalService,
    private snackbarService: SnackbarService,
    private zaakService: ZaakService,
  ) {
  }

  /**
   * Updates the component using a public interface.
   */
  public update() {
    this.getContextData();
  }

  //
  // Getters / setters.
  //

  /**
   * Whether user can force edit a closed case.
   * @returns {boolean}
   */
  get canForceEdit(): boolean {
    return !this.zaak.resultaat || this.zaak.kanGeforceerdBijwerken;
  }

  //
  // Angular lifecycle.
  //

  /**
   * A lifecycle hook that is called after Angular has initialized all data-bound properties of a directive. Define an
   * ngOnInit() method to handle any additional initialization tasks.
   */
  ngOnInit(): void {
    this.getContextData()
  }

  //
  // Context.
  //

  /**
   * Fetches the user permissions.
   */
  getContextData(): void {
    this.zaakService.listCaseUsers(this.zaak.bronorganisatie, this.zaak.identificatie).subscribe(
      (userPermissions: UserPermission[]): void => {
        this.userPermissions = userPermissions;
        this.shortUserPermissions = userPermissions.slice(0, 3);

        this.isLoading = false;
      },
      this.reportError.bind(this)
    );
  }

  /**
   * Create table data
   * @param permissions
   */
  getUserTable(permissions) {
    this.table = this.userPermissionsAsTable(permissions);
  }

  /**
   * Returns user permissions as table.
   * @param {UserPermission[]} userPermissions
   * @return {Table}
   */
  userPermissionsAsTable(permissions: ZaakPermission[]) {
    const headData = ['Rechten', 'Reden', 'Commentaar', ''];

    const bodyData = permissions.map((permission: ZaakPermission) => {

      const cellData: RowData = {
        cellData: {
          permission: {
            type: 'chip',
            label: permission.permission
          },
          reason: permission.reason,
          comment: permission.comment,
          // Hide button if case is closed and the user is not allowed to force edit
          delete: !this.zaak.resultaat || this.zaak.kanGeforceerdBijwerken ? {
            type: 'button',
            label: 'Verwijderen',
            value: permission,
          } : '',
        },
      }
      return cellData;
    })

    return new Table(headData, bodyData);
  }

  //
  // Events.
  //

  /**
   * Opens modal.
   * @param {string} id
   */
  openModal(id: string) {
    this.modalService.open(id);
  }

  /**
   * Expand table rows.
   */
  expand() {
    this.isExpanded = !this.isExpanded;
  }

  /**
   * Get called when the remove permission button (in the table) is clicked.
   * Opens the confirm dialog.
   * @param event
   */
  buttonClick(event) {
    this.selectedPermission = event.delete;
    this.modalService.open('delete-permission-modal')
  }

  /**
   * Deletes user permission.
   */
  deletePermission(): void {
    const permission = this.selectedPermission;
    this.permissionsService.deletePermission(permission).subscribe(
      () => {
        this.getContextData();
        this.closeDeletePermission();
      }, (error) => {
        this.reportError(error);
        this.getContextData();
        this.closeDeletePermission();
      }
    );
  }

  /**
   * Closes the delete permission dialog.
   */
  closeDeletePermission() {
    this.selectedPermission = null;
    this.modalService.close('delete-permission-modal');
  }

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    this.isLoading = false;

    if (error.error?.detail) {
      this.errorDetailMessage = error.error?.detail;
    } else {
      console.error(error);
      this.snackbarService.openSnackBar(this.errorMessage, 'Sluiten', 'warn');
    }
  }
}
