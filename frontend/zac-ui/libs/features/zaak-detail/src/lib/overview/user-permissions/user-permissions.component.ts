import {Component, Input, OnInit} from '@angular/core';
import { ZaakPermission, UserPermission, Table, Zaak } from '@gu/models';
import {ZaakService} from "@gu/services";
import {PermissionsService} from './permissions.service';
import { ModalService, TableButtonClickEvent } from '@gu/components';

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
    errorDetailMessage = '';

    /** @type {boolean} Whether this component is loading. */
    isLoading = false;

    /** @type {Table} The Table to render. */
    table: Table = null;

    /** @type {Table} The short version of Table to render. */
    shortTable: Table = null;

    /** @type {UserPermission[]} The user permissions. */
    userPermissions: UserPermission[] = [];

    /** @type {boolean} Wether table rows are all shown */
    isExpanded = false;

    constructor(
      private permissionsService: PermissionsService,
      private modalService: ModalService,
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
                this.table = this.userPermissionsAsTable(userPermissions);

                this.shortTable = {...this.table};
                this.shortTable.bodyData = this.shortTable.bodyData.slice(0, 3);

                this.isLoading = false;
            },
            this.reportError.bind(this),
        );
    }


    /**
     * Returns user permissions as table.
     * @param {UserPermission[]} userPermissions
     * @return {Table}
     */
    userPermissionsAsTable(userPermissions: UserPermission[]): Table {
        const bodyData = userPermissions.reduce((acc, userPermission) => {
            const userRows = userPermission.permissions.map((permission: ZaakPermission) => ({
                cellData: {
                    user: {
                        type: 'text',
                        label: userPermission.username,
                    },
                    permission: {
                        type: 'chip',
                        label: permission.permission
                    },
                    // Hide button if case is closed and the user is not allowed to force edit
                    delete: !this.zaak.resultaat || this.zaak.kanGeforceerdBijwerken ? {
                        type: 'button',
                        label: 'Verwijderen',
                        value: permission,
                    } : ''
                },
                nestedTableData: new Table(['Reden', 'Commentaar'], [{
                    cellData: {
                        reason: permission.reason,
                        comment: permission["comment"]
                    }
                },
                ]),
                expandData: ''
            }));
            return [...acc, ...userRows];
        }, []);

        return new Table(
            [
                'Gebruiker',
                'Rechten',
                'Acties',
            ], bodyData);
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
     * Gets called when delete button is clicked, remover user permission.
     * @param {TableButtonClickEvent} event
     */
    buttonClick(event: TableButtonClickEvent): void {
        const permission = event.delete;
        this.permissionsService.deletePermission(permission).subscribe(
            (): void => {
                this.getContextData();
            },
            this.reportError.bind(this),
        );
    }

  //
  // Error handling.
  //

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    this.isLoading = false;

    if(error.error?.detail) {
      this.errorDetailMessage = error.error?.detail;
    } else {
      console.error(error);
    }
  }
}
