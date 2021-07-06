import {Component, Input, OnInit} from '@angular/core';
import {Table} from '@gu/models';
import {Permission, UserPermission} from './user-permission';
import {UserPermissionsService} from './user-permissions.service';
import {TableButtonClickEvent} from '../../../../../shared/ui/components/src/lib/components/table/table';


/**
 * <gu-user-permissions [bronorganisatie]="bronorganisatie" [identificatie]="identificatie"></gu-user-permissions>
 *
 * Show user permissions for bronorganisatie/identificatie.
 *
 * Requires bronorganisatie: string input to identify the organisation.
 * Requires identificatie: string input to identify the case (zaak).
 */
@Component({
    providers: [UserPermissionsService],
    selector: 'gu-user-permissions',
    styleUrls: ['./user-permissions.component.scss'],
    templateUrl: './user-permissions.component.html',
})
export class UserPermissionsComponent implements OnInit {
    @Input() bronorganisatie: string;
    @Input() identificatie: string;

    /** @type {boolean} Whether this component is loading. */
    isLoading = false;

    /** @type {Table|null} The Table to render. */
    table = null;

    /** @type {UserPermission[]} The user permissions. */
    userPermissions: UserPermission[] = [];

    constructor(private userPermissionsService: UserPermissionsService) {
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
        this.userPermissionsService.getUserPermissions(this.bronorganisatie, this.identificatie).subscribe(
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
            const userRows = userPermission.permissions.map((permission: Permission) => ({
                cellData: {
                    user: {
                        type: 'text',
                        label: userPermission.username,
                    },
                    permission: {
                        type: 'chip',
                        label: permission.permission
                    },
                    delete: {
                        type: 'button',
                        label: 'Verwijderen',
                        value: permission,
                    }
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
     * Gets called when delete button is clicked, remover user permission.
     * @param {TableButtonClickEvent} event
     */
    onButtonClick(event: TableButtonClickEvent): void {
        const permission = event.delete;
        this.userPermissionsService.deletePermission(permission).subscribe(
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
