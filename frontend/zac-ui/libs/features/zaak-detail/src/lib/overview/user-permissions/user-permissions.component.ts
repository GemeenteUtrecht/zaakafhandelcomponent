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

    /** @type {boolean} Whether this component is loading. */
    isLoading = false;

    /** @type {Table|null} The Table to render. */
    table = null;

    /** @type {UserPermission[]} The user permissions. */
    userPermissions: UserPermission[] = [];

    constructor(
      private permissionsService: PermissionsService,
      private modalService: ModalService,
      private zaakService: ZaakService,
    ) {
    }

    //
    // Getters / setters.
    //

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
                this.isLoading = false;
            },
            (error: any): void => {
                console.error(error);
                this.isLoading = false;
            },
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
     * Gets called when delete button is clicked, remover user permission.
     * @param {TableButtonClickEvent} event
     */
    buttonClick(event: TableButtonClickEvent): void {
        const permission = event.delete;
        this.permissionsService.deletePermission(permission).subscribe(
            (): void => {
                this.getContextData();
            },
            (error: any): void => {
                console.error(error);
                this.isLoading = false;
                this.getContextData();
            },
        );
    }
}
