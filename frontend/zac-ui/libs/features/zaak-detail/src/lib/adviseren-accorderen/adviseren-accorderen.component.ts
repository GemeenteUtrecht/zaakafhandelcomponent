import {Component, Input, OnInit} from '@angular/core';
import {ModalService, SnackbarService} from '@gu/components';
import {ExtensiveCell, RowData, Table} from '@gu/models';
import {ReviewRequestDetails, ReviewRequestSummary} from '@gu/kownsl';
import {ReviewRequestsService} from './review-requests.service';


/**
 * <gu-adviseren-accorderen [bronorganisatie]="bronorganisatie" [identificatie]="identificatie"></gu-adviseren-accorderen>
 *
 * Show review requests for bronorganisatie/identificatie.
 *
 * Requires bronorganisatie: string input to identify the organisation.
 * Requires identificatie: string input to identify the case (zaak).
 */
@Component({
  selector: 'gu-adviseren-accorderen',
  templateUrl: './adviseren-accorderen.component.html',
  styleUrls: ['./adviseren-accorderen.component.scss'],
})
export class AdviserenAccorderenComponent implements OnInit {
  @Input() bronorganisatie: string;
  @Input() identificatie: string;

  readonly errorMessage = 'Er is een fout opgetreden bij het laden van advies/akkoord aanvragen.'

  /** @type {boolean} Whether the summary is loading. */
  isSummariesLoading = false

  /** @type {boolean} Whether details are loading. */
  isDetailsLoading = false;

  /** @type {ReviewRequestSummary[]} The review request summaries used for initial list. */
  reviewRequestSummaries: ReviewRequestSummary[];

  /** @type {Object<string, ReviewRequestDetails>} The review request details by id. */
  reviewRequestDetails: { [id: string]: ReviewRequestDetails } = {};

  /** @type {ReviewRequestDetails} The details of the selected review request. */
  selectedReviewRequestDetails: ReviewRequestDetails;

  /** @type {ReviewRequestSummary} The selected review request. */
  selectedReviewRequestSummary: ReviewRequestSummary;

  tableData: Table;

  constructor(
    private modalService: ModalService,
    private reviewRequestsService: ReviewRequestsService,
    private snackbarService: SnackbarService,
  ) {
  }

  /**
   * Updates the component using a public interface.
   */
  public update() {
    this.getContextData();
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
  // Context.
  //

  /**
   * Fetches the review requests summaries/details.
   */
  getContextData(): void {
    this.isSummariesLoading = true;

    this.reviewRequestsService.listReviewRequestSummariesForCase(this.bronorganisatie, this.identificatie).subscribe(
      (reviewRequestSummaries) => {
        this.reviewRequestSummaries = reviewRequestSummaries;
        this.fetchReviewRequestDetails(reviewRequestSummaries);
      },
      this.reportError.bind(this),
      () => this.isSummariesLoading = false,
    );
  }

  /**
   * Fetches review request details for for review requests summaries.
   * Filters to review request summaries to those not pristine first, to reduce API load.
   * @param {ReviewRequestSummary[]} reviewRequestSummaries
   */
  fetchReviewRequestDetails(reviewRequestSummaries: ReviewRequestSummary[]): void {
    const relevantUuids = reviewRequestSummaries.filter((r) => !this.reviewRequestsService.isReviewRequestPristine(r))
      .map((r) => r.id);

    this.isDetailsLoading = true;

    this.tableData = this.reviewRequestSummaryAsTable(this.reviewRequestSummaries);

    this.reviewRequestsService.retrieveReviewRequestDetailsBatch(relevantUuids).subscribe(
      (reviewRequestDetails) => {
        this.reviewRequestDetails[reviewRequestDetails.id] = reviewRequestDetails;
        this.tableData = this.reviewRequestSummaryAsTable(this.reviewRequestSummaries);
      },
      this.reportError.bind(this),
      () => {
        this.isDetailsLoading = false;
      }
    );
  }

  /**
   * Returns the details object for a review request summary.
   * @param {ReviewRequestSummary} reviewRequestSummary
   * @return {ReviewRequestDetails}
   */
  getReviewRequestDetailsForSummary(reviewRequestSummary: ReviewRequestSummary): ReviewRequestDetails | null {
    return this.reviewRequestDetails[reviewRequestSummary.id] || null;
  }

  /**
   * Returns review request summary as table.
   * @param {ReviewRequestSummary[]} reviewRequestSummaries
   * @return {Table}
   */
  reviewRequestSummaryAsTable(reviewRequestSummaries: ReviewRequestSummary[]): Table {
    const table = new Table(['', 'Resultaat', 'Soort aanvraag', 'Opgehaald', 'Laatste update', ''], []);

    table.bodyData = reviewRequestSummaries.map((reviewRequestSummary): RowData => {
      const reviewRequestDetails = this.getReviewRequestDetailsForSummary(reviewRequestSummary);
      const [icon, iconColor] = this.reviewRequestsService.getReviewRequestIcon(reviewRequestSummary, reviewRequestDetails);
      const status = this.reviewRequestsService.getReviewRequestStatus(reviewRequestSummary, reviewRequestDetails);
      const date = reviewRequestDetails ? this.reviewRequestsService.getReviewRequestLastUpdate(reviewRequestDetails) : null;

      return {
        cellData: {
          'icon': {
            iconColor: iconColor,
            label: icon,
            type: 'icon',
          } as ExtensiveCell,

          'result': status.label,

          'type': reviewRequestSummary.reviewType === 'approval' ? 'Akkoord aanvraag' : 'Advies aanvraag',

          'opgehaald': `${reviewRequestSummary.completed}/${reviewRequestSummary.numAssignedUsers}`,

          'last_update': {
            type: date === null ? 'text' : 'date',
            date: String(date),
          } as ExtensiveCell,

          'cancel': reviewRequestSummary.canLock && (reviewRequestSummary.completed < reviewRequestSummary.numAssignedUsers) ? {
            type: 'button',
            label: 'Annuleren',
            value: reviewRequestSummary
          } : '',
        },

        clickOutput: reviewRequestSummary.completed > 0 ? reviewRequestSummary : null
      } as RowData;
    });

    return table;
  }

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    this.snackbarService.openSnackBar(this.errorMessage, 'Sluiten', 'warn');
    console.error(error);
  }

  //
  // Events.
  //

  /**
   * Close modal
   * @param modalId
   */
  closeModal(modalId: string): void {
    this.modalService.open(modalId);
  }

  /**
   * Gets called when a table button is clicked.
   * @param {event} event
   */
  tableButtonClick(event): void {
    this.selectedReviewRequestSummary = event.cancel;
    this.modalService.open('cancel-review-modal')
  }

  /**
   * Gets called when a table row is clicked.
   * @param {ReviewRequestSummary} reviewRequestSummary
   */
  tableClick(reviewRequestSummary: ReviewRequestSummary): void {
    this.selectedReviewRequestSummary = reviewRequestSummary;
    this.selectedReviewRequestDetails = this.getReviewRequestDetailsForSummary(reviewRequestSummary);
    this.modalService.open('adviseren-accorderen-detail-modal')
  }
}
