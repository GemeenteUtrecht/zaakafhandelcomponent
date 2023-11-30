import { Component, EventEmitter, OnInit, Output, ViewChild } from '@angular/core';
import { ModalService, PaginatorComponent, SnackbarService } from '@gu/components';
import {
  ExtensiveCell,
  RowData,
  Table,
  WorkstackAdvice,
  WorkstackApproval,
  WorkstackCase,
  WorkstackReview
} from '@gu/models';
import { zakenTableHead } from '../../constants/zaken-tablehead';
import { FeaturesWorkstackService } from '../../features-workstack.service';
import { reviewsTableHead } from '../../constants/reviews-tablehead';

@Component({
  selector: 'gu-workstack-review-requests',
  templateUrl: './workstack-review-requests.component.html',
  styleUrls: ['./workstack-review-requests.component.scss']
})
export class WorkstackReviewRequestsComponent implements OnInit {
  @ViewChild(PaginatorComponent) paginator: PaginatorComponent;
  reviewsData: {count: number, next: string, previous: string, results: WorkstackReview[]};
  reviewsTableData: Table = new Table(reviewsTableHead, []);

  selectedReviewRequest: WorkstackReview;
  isLoading: boolean;
  pageNumber = 1;
  sortValue: any;

  @Output() reviewDataOutput: EventEmitter<any> = new EventEmitter<any>();

  constructor(
    private workstackService: FeaturesWorkstackService,
    private snackbarService: SnackbarService,
    private modalService: ModalService
  ) { }

  get nReviews(): number {
    return this.reviewsData?.count;
  };

  get table(): Table {
    if(this.selectedReviewRequest?.approvals) {
      return this.formatTableDataApproval(this.selectedReviewRequest)
    }

    if(this.selectedReviewRequest?.advices){
      return this.formatTableDataAdvice(this.selectedReviewRequest)
    }

    return null;
  }

  ngOnInit(): void {
    this.getContextData(1);
  }

  /**
   * Fetches the reviews data
   * @param page
   * @param sortData
   */
  getContextData(page, sortData?) {
    this.isLoading = true;
    this.workstackService.getWorkstackReviews(page, sortData).subscribe(
      (res) => {
        this.reviewsData = res
        this.reviewDataOutput.emit(res);
        this.reviewsTableData = new Table(reviewsTableHead, this.getReviewsTableRows(this.reviewsData.results));
        this.isLoading = false;
      }, this.reportError.bind(this))
  }

  /**
   * Generate table rows
   * @param {WorkstackReview[]} reviews
   * @returns {RowData[]}
   */
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

  // Events.

  /**
   * Gets called when a table row is clicked.
   * @param {ReviewRequestSummary} reviewRequestSummary
   */
  tableRowClick(review): void {
    this.selectedReviewRequest = review;
    this.modalService.open('workstack-review-modal')
  }

  /**
   * Sorts the zaken (cases).
   * @param {{value: string, order: string}} sortValue
   */
  sortTable(sortValue): void {
    this.paginator.firstPage();
    this.pageNumber = 1;
    this.sortValue = sortValue;
    this.getContextData(this.pageNumber, this.sortValue);
  }

  /**
   * When paginator gets fired.
   * @param page
   */
  onPageSelect(page) {
    this.pageNumber = page.pageIndex + 1;
    this.getContextData(this.pageNumber, this.sortValue);
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
        : 'Advies/akkoord ophalen mislukt';

    this.isLoading = false;
    this.snackbarService.openSnackBar(errorMessage, 'Sluiten', 'warn');
    console.error(res);
  }
}
