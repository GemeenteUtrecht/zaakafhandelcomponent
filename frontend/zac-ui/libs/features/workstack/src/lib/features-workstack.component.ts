import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { RowData, Table, UserTask, UserTaskZaak, WorkstackCase } from '@gu/models';
import {FeaturesWorkstackService} from './features-workstack.service';
import { tabs, Tab, tabIndexes } from './constants/tabs';
import {zakenTableHead} from './constants/zaken-tablehead';
import {AccessRequests} from './models/access-request';
import {AdHocActivities} from './models/activities';
import {SnackbarService} from '@gu/components';
import { WorkstackChecklist } from './models/checklist';
import { tasksTableHead } from './constants/tasks-tablehead';

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
    zakenData: {count: number, next: string, previous: string, results: WorkstackCase[]};
    taskData: {count: number, next: string, previous: string, results: UserTask[]};
    taskPage: number;
    groupTaskData: {count: number, next: string, previous: string, results: UserTask[]};
    groupTaskPage: number;
    activitiesData: {count: number, next: string, previous: string, results: AdHocActivities[]};
    groupActivitiesData: {count: number, next: string, previous: string, results: AdHocActivities[]};
    accessRequestData: {count: number, next: string, previous: string, results: AccessRequests[]};
    checkListData: WorkstackChecklist[];
    groupCheckListData: WorkstackChecklist[];

    zakenTableData: Table = new Table(zakenTableHead, []);
    tasksTableData: Table = new Table(tasksTableHead, []);
    groupTasksTableData: Table = new Table(tasksTableHead, []);

    isLoading: boolean;

    readonly errorMessage = 'Er is een fout opgetreden bij het ophalen van de werkvoorraad';

    /**
     * Constructor method.
     * @param {FeaturesWorkstackService} workstackService
     * @param {SnackbarService} snackbarService
     */
    constructor(private cdRef: ChangeDetectorRef, private workstackService: FeaturesWorkstackService, private snackbarService: SnackbarService) {
    }


    //
    // Getters / setters.
    //

    get nActivities(): number {
      return this.activitiesData?.count + this.checkListData?.length
    };

    get nGroupActivities(): number {
      return this.groupActivitiesData?.count + this.groupCheckListData?.length
    };

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
    getZakenTableRows(zaken: WorkstackCase[]): RowData[] {
        return zaken.map((element) => {
            const zaakUrl = `/ui/zaken/${element.bronorganisatie}/${element.identificatie}/acties`;

            const cellData: RowData = {
                cellData: {
                    identificatie: {
                        type: 'link',
                        label: element.identificatie,
                        url: zaakUrl,
                    },
                    omschrijving: element.omschrijving,
                    zaaktype: element.zaaktype.omschrijving,
                    zaakstatus: element.status?.statustype || '',
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
    getTasksTableRows(tasks: UserTask[]): RowData[] {
      return tasks.map((element) => {
        const zaakUrl = `/ui/zaken/${element.zaak.bronorganisatie}/${element.zaak.identificatie}/acties`;

        const cellData: RowData = {
          cellData: {
            task: element.task,
            identificatie: {
              type: 'link',
              label: element.zaak.identificatie,
              url: zaakUrl,
            },
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
                // Zaken
                this.zakenData = res[0];
                this.zakenTableData.bodyData = this.getZakenTableRows(
                  this.zakenData.results
                );

                // Tasks
                this.taskData = res[1];
                this.tasksTableData.bodyData = this.getTasksTableRows(
                  this.taskData.results
                );

                // Group tasks
                this.groupTaskData = res[2];
                this.groupTasksTableData.bodyData = this.getTasksTableRows(
                  this.groupTaskData.results
                );

                // Activities
                this.activitiesData = res[3];
                this.groupActivitiesData = res[4];
                this.accessRequestData = res[5];
                this.checkListData = res[6];
                this.groupCheckListData = res[7];
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
                    this.zakenTableData.bodyData = this.getZakenTableRows(
                        this.zakenData.results
                    );
                }, this.reportError.bind(this)
            );
    }

    //
    // Events
    //

    /**
     * When paginator gets fired.
     * @param page
     */
    onPageSelect(page, paginatorType: string) {
      this.workstackService
        .getWorkstack([tabs[tabIndexes[paginatorType]]], page.pageIndex + 1)
        .subscribe(
          (res) => {
            switch (paginatorType) {
              case tabs[0].component:
                this.zakenData = res[0];
                this.zakenTableData = new Table(zakenTableHead, []);
                this.zakenTableData.bodyData = this.getZakenTableRows(this.zakenData.results);
                break;
              case tabs[1].component:
                this.taskData = res[0];
                this.tasksTableData = new Table(tasksTableHead, []);
                this.tasksTableData.bodyData = this.getTasksTableRows(this.taskData.results);
                break;
              case tabs[2].component:
                this.groupTaskData = res[0];
                this.groupTasksTableData = new Table(tasksTableHead, []);
                this.groupTasksTableData.bodyData = this.getTasksTableRows(this.groupTaskData.results);
                break;
              case tabs[3].component:
                this.activitiesData = res[0];
                break;
              case tabs[4].component:
                this.groupActivitiesData = res[0];
                break;
              case tabs[5].component:
                this.accessRequestData = res[0];
                break;
              case tabs[6].component:
                this.checkListData = res[0];
                break;
              case tabs[7].component:
                this.groupCheckListData = res[0];
                break;
            }
            this.cdRef.detectChanges();
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
