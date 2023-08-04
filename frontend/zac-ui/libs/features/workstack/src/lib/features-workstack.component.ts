import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import {
  ExtensiveCell,
  RowData,
  Table,
  UserTask, WorkstackAdvice,
  WorkstackApproval,
  WorkstackCase,
  WorkstackReview,
  Zaak
} from '@gu/models';
import {FeaturesWorkstackService} from './features-workstack.service';
import { tabs, Tab, tabIndexes } from './constants/tabs';
import {zakenTableHead} from './constants/zaken-tablehead';
import {AccessRequests} from './models/access-request';
import {AdHocActivities} from './models/activities';
import { ModalService, SnackbarService } from '@gu/components';
import { WorkstackChecklist } from './models/checklist';
import { tasksTableHead } from './constants/tasks-tablehead';
import { ReviewRequestDetails, ReviewRequestSummary } from '@gu/kownsl';
import { reviewsTableHead } from './constants/reviews-tablehead';

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
    reviewsData: {count: number, next: string, previous: string, results: WorkstackReview[]};
    accessRequestData: {count: number, next: string, previous: string, results: AccessRequests[]};
    checkListData: WorkstackChecklist[];
    groupCheckListData: WorkstackChecklist[];

    zakenTableData: Table = new Table(zakenTableHead, []);
    tasksTableData: Table = new Table(tasksTableHead, []);
    groupTasksTableData: Table = new Table(tasksTableHead, []);
    reviewsTableData: Table = new Table(reviewsTableHead, []);

    selectedReviewRequest: WorkstackReview;

    isLoading: boolean;

    readonly errorMessage = 'Er is een fout opgetreden bij het ophalen van de werkvoorraad';

    /**
     * Constructor method.
     * @param {FeaturesWorkstackService} workstackService
     * @param {SnackbarService} snackbarService
     */
    constructor(
      private cdRef: ChangeDetectorRef,
      private workstackService: FeaturesWorkstackService,
      private snackbarService: SnackbarService,
      private modalService: ModalService) {
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

    get nReviews(): number {
      return this.reviewsData?.count;
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
            identificatie: {
              type: 'link',
              label: element.zaak.identificatie,
              url: zaakUrl,
            },
            task: element.task,
            omschrijving: element.zaak.omschrijving,
            zaaktype: element.zaak.zaaktype.omschrijving,
            deadline: {
              type: element.zaak.deadline ? 'date' : 'text',
              date: element.zaak.deadline
            },
          },
        };
        return cellData;
      });
    }

  getReviewsTableRows(reviews: WorkstackReview[]): RowData[] {
    return reviews.map((review) => {
      const zaakUrl = review.zaak ? `/ui/zaken/${review.zaak.bronorganisatie}/${review.zaak.identificatie}/acties` : null;
      const reviewType = review.reviewType === 'advice' ? 'Advies' : 'Akkoord';
      const openReviews = review.openReviews.length === 0 ? '-' : review.openReviews.length.toString()
      let replies = review.reviewType === 'advice' ? review.advices.length.toString() : review.approvals.length.toString();
      replies = replies === '0' ? '-' : replies;

      const cellData: RowData = {
        cellData: {
          identificatie: zaakUrl ?
            {
            type: 'link',
            label: review.zaak.identificatie,
            url: zaakUrl,
            } : '',
          omschrijving: zaakUrl ? review.zaak.omschrijving : '',
          reviewType: reviewType,
          openReviews: openReviews,
          replies: replies,
        },
        clickOutput: review
      };

      return cellData;
    });
  }

    /**
     * Returns the path to zaak.
     * @param {Zaak} zaak
     * @return {string}
     */
    getZaakPath(zaak: Zaak): string {
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

                // Reviews
                this.reviewsData = res[3];
                this.reviewsTableData.bodyData = this.getReviewsTableRows(
                  this.reviewsData.results
                );

                // Activities
                this.activitiesData = res[4];
                this.groupActivitiesData = res[5];
                this.accessRequestData = res[6];
                this.checkListData = res[7];
                this.groupCheckListData = res[8];
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

  /**
   * Sorts the reviews.
   * @param {{value: string, order: string}} sortValue
   */
  sortReviews(sortValue): void {
    const sortBy = sortValue.order ? sortValue.value : undefined  // Yes.
    const sortOrder = sortValue.order ? sortValue.order : undefined  // Yes.
    this.workstackService
      .getWorkstackReview(sortBy, sortOrder)
      .subscribe(
        (res) => {
          this.reviewsData = res;
          this.reviewsTableData.bodyData = this.getZakenTableRows(
            this.zakenData.results
          );
        }, this.reportError.bind(this)
      );
  }

  /**
   * Return the table to render.
   * @return {Table}
   */
  get table(): Table {
    if(this.selectedReviewRequest?.approvals) {
      return this.formatTableDataApproval(this.selectedReviewRequest)
    }

    if(this.selectedReviewRequest?.advices){
      return this.formatTableDataAdvice(this.selectedReviewRequest)
    }

    return null;
  }

  /**
   * Returns table for advices of the selected review.
   * @param {WorkstackReview} reviewRequestDetails
   * @return {Table}
   */
  formatTableDataAdvice(reviewRequestDetails: WorkstackReview): Table {
    const headData = ['Advies', 'Van', 'Gegeven op', 'Documentadviezen'];

    const bodyData = reviewRequestDetails.advices.map((review: WorkstackAdvice) => {

      const cellData: RowData = {
        cellData: {
          advies: review.advice,
          van: review.author.fullName,

          datum: {
            type: review.created ? 'date' : 'text',
            date: review.created
          } as ExtensiveCell,

        },
      }
      return cellData;
    })

    return new Table(headData, bodyData);
  }

  /**
   * Returns table for approvals of the selected review.
   * @param {WorkstackReview} reviewRequestDetails
   * @return {Table}
   */
  formatTableDataApproval(reviewRequestDetails: WorkstackReview): Table {
    const headData = ['Resultaat', 'Van', 'Gegeven op', 'Toelichting'];

    const bodyData = reviewRequestDetails.approvals.map((review: WorkstackApproval) => {
      const icon = review.status === 'Akkoord' ? 'done' : 'close'
      const iconColor = review.status === 'Akkoord' ? 'green' : 'red'

      const cellData: RowData = {
        cellData: {
          akkoord: {
            type: 'icon',
            label: icon,
            iconColor: iconColor
          } as ExtensiveCell,

          van: review.author.fullName,
          datum: {
            type: review.created ? 'date' : 'text',
            date: review.created
          } as ExtensiveCell,

          toelichting: review.toelichting
        }
      }

      return cellData;
    })

    return new Table(headData, bodyData);
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
                this.reviewsData = res[0];
                this.reviewsTableData = new Table(reviewsTableHead, []);
                this.reviewsTableData.bodyData = this.getReviewsTableRows(
                  this.reviewsData.results
                );
                break;
              case tabs[4].component:
                this.activitiesData = res[0];
                break;
              case tabs[5].component:
                this.groupActivitiesData = res[0];
                break;
              case tabs[6].component:
                this.accessRequestData = res[0];
                break;
              case tabs[7].component:
                this.checkListData = res[0];
                break;
              case tabs[8].component:
                this.groupCheckListData = res[0];
                break;
            }
            this.cdRef.detectChanges();
          }, this.reportError.bind(this)
        );
    }

    /**
     * Gets called when a table row is clicked.
     * @param {ReviewRequestSummary} reviewRequestSummary
     */
    tableRowClick(review): void {
      this.selectedReviewRequest = review;
      this.modalService.open('workstack-review-modal')
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
