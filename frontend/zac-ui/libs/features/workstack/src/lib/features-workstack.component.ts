import {Component, OnInit} from '@angular/core';
import {RowData, Zaak, Table, UserTask, UserTaskZaak} from '@gu/models';
import {FeaturesWorkstackService} from './features-workstack.service';
import {tabs, Tab} from './constants/tabs';
import {tableHead} from './constants/zaken-tablehead';
import {AccessRequests} from './models/access-request';
import {AdHocActivities} from './models/activities';
import {SnackbarService} from '@gu/components';


/**
 * <gu-features-workstack></gu-features-workstack>
 *
 * Shows workstack for the user.
 */
@Component({
    selector: 'gu-features-workstack',
    templateUrl: './features-workstack.component.html',
    styleUrls: ['./features-workstack.component.scss'],
})
export class FeaturesWorkstackComponent implements OnInit {
    tabs: Tab[] = tabs;
    currentActiveTab = 0;

    allData: any;
    zakenData: Zaak[];
    taskData: UserTask[];
    groupTaskData: UserTask[];
    activitiesData: AdHocActivities[];
    accessRequestData: AccessRequests[];

    zakenTableData: Table = new Table(tableHead, []);

    isLoading: boolean;

    readonly errorMessage = 'Er is een fout opgetreden bij het ophalen van de werkvoorraad';

    /**
     * Constructor method.
     * @param {FeaturesWorkstackService} workstackService
     * @param {SnackbarService} snackbarService
     */
    constructor(private workstackService: FeaturesWorkstackService, private snackbarService: SnackbarService) {
    }

    //
    // Angular lifecycle.
    //

    /**
     * A lifecycle hook that is called after Angular has initialized all data-bound properties of a directive. Define an
     * ngOnInit() method to handle any additional initialization tasks.
     */
    ngOnInit(): void {
        this.getContextData();
    }

    //
    // Getters / setters.
    //

    /**
     * Returns the table rows.
     * @param {Zaak[]} zaken
     * @return {RowData}
     */
    getTableRows(zaken: Zaak[]): RowData[] {
        return zaken.map((element) => {
            const zaakUrl = `/ui/zaken/${element.bronorganisatie}/${element.identificatie}`;

            const cellData: RowData = {
                cellData: {
                    identificatie: {
                        type: 'link',
                        label: element.identificatie,
                        url: zaakUrl,
                    },
                    omschrijving: element.omschrijving,
                    zaaktype: element.zaaktype.omschrijving,
                    startdatum: {
                        type: element.startdatum ? 'date' : 'text',
                        date: element.startdatum
                    },
                    einddatum: {
                        type: element.deadline ? 'date' : 'text',
                        date: element.deadline
                    },
                    trust: element.vertrouwelijkheidaanduiding
                },
            };
            return cellData;
        });
    }

    /**
     * Returns the path to zaak.
     * @param {Zaak} zaak
     * @return {string}
     */
    getZaakPath(zaak: UserTaskZaak): string {
        return `/zaken/${zaak.bronorganisatie}/${zaak.identificatie}`;
    }

    //
    // Context.
    //

    /**
     * Fetches the workstack data.
     */
    getContextData(): void {
        this.isLoading = true;
        this.workstackService.getWorkstack(tabs).subscribe(
            (res) => {
                this.allData = res;
                this.zakenData = res[0];
                this.taskData = res[1];
                this.groupTaskData = res[2];
                this.activitiesData = res[3];
                this.accessRequestData = res[4];
                this.zakenTableData.bodyData = this.getTableRows(
                    this.zakenData
                );
                this.isLoading = false;
            }, this.reportError.bind(this)
        );
    }

    /**
     * Updates the context, then activates tab.
     * @param {number} tab
     */
    updateContextData(tab: number): void {
        this.getContextData();
        this.currentActiveTab = tab;
    }

    /**
     * Sorts the zaken (cases).
     * @param {{value: string, order: string}} sortValue
     */
    sortZaken(sortValue): void {
        const sortBy = sortValue.order ? sortValue.value : undefined  // Yes.
        const sortOrder = sortValue.order ? sortValue.order : undefined  // Yes.
        this.workstackService
            .getWorkstackZaken(sortBy, sortOrder)
            .subscribe(
                (res) => {
                    this.zakenData = res;
                    this.zakenTableData.bodyData = this.getTableRows(
                        this.zakenData
                    );
                }, this.reportError.bind(this)
            );
    }

    //
    // Error handling.
    //

    /**
     * Error callback.
     * @param res
     */
    reportError(res) {
        const errorMessage = res.error?.detail
            ? res.error.detail
            : res.error?.nonFieldErrors
                ? res.error.nonFieldErrors[0]
                : this.errorMessage;

        this.isLoading = false;
        this.snackbarService.openSnackBar(errorMessage, 'Sluiten', 'warn');
        console.error(res);
    }
}
