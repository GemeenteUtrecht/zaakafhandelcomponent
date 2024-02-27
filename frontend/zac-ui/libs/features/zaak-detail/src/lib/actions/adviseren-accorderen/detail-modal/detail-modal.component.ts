import {Component, Input} from '@angular/core';
import {Observable} from 'rxjs';
import {Author, ReviewRequestDetails, ReviewRequestSummary} from '@gu/kownsl';
import {ExtensiveCell, ReadWriteDocument, RowData, Table} from '@gu/models';
import {ApplicationHttpClient} from '@gu/services';
import {Review, ReviewDocument} from './detail-modal.interface';
import { ReviewRequestsService } from '../review-requests.service';
import { ModalService, SnackbarService } from '@gu/components';


/**
 * <gu-detail-modal [reviewRequestDetails]="reviewRequestDetails"></gu-gu-detail-modal>
 *
 * Show review details.
 *
 * Requires reviewRequestDetails: ReviewRequestDetails input to show in a modal.
 */
@Component({
  selector: 'gu-detail-modal',
  templateUrl: './detail-modal.component.html',
  styleUrls: ['./detail-modal.component.scss']
})
export class DetailModalComponent  {
  @Input() reviewRequestDetails: ReviewRequestDetails;
  @Input() reviewRequestSummary: ReviewRequestSummary;
  @Input() isLoading: boolean;


  constructor(
    private http: ApplicationHttpClient,
    private reviewRequestService: ReviewRequestsService,
    private modalService: ModalService,
    private snackbarService: SnackbarService,
  ) {
  }

  //
  // Getters / setters.
  //

  /**
   * Returns the title to render.
   * @return {string}
   */
  get title(): string {
    switch (this.reviewRequestDetails?.reviewType) {
      case 'approval':
        return 'Accorderingen';
      case 'advice':
        return 'Adviezen';
      default:
        return '';
    }
  }

  /**
   * Return the table to render.
   * @return {Table}
   */
  get table(): Table {
    if(this.reviewRequestDetails?.approvals) {
      return this.formatTableDataApproval(this.reviewRequestDetails)
    }

    if(this.reviewRequestDetails?.advices){
      return this.formatTableDataAdvice(this.reviewRequestDetails)
    }

    return null;
  }

  //
  // Context.
  //


  /**
   * Returns table for advices of reviewRequestDetails.
   * @param {ReviewRequestDetails} reviewRequestDetails
   * @return {Table}
   */
  formatTableDataAdvice(reviewRequestDetails: ReviewRequestDetails): Table {
    const headData = ['Advies', 'Van', 'Gegeven op', 'Documentadviezen'];

    const bodyData = reviewRequestDetails.advices.map((review: Review) => {
      const author = this.getAuthorName(review.author);
      const docAdviezen = review.reviewDocuments ? review.reviewDocuments.length.toString() : '-';
      const reviewDocumentTableData = review.reviewDocuments?.length > 0 ? this.formatTableReviewDoc(review.reviewDocuments) : null;

      const cellData: RowData = {
        cellData: {
          advies: review.advice,
          van: author,

          datum: {
            type: review.created ? 'date' : 'text',
            date: review.created
          } as ExtensiveCell,

          docAdviezen: docAdviezen
        },
        nestedTableData: reviewDocumentTableData,
      }
      return cellData;
    })

    return new Table(headData, bodyData);
  }

  /**
   * Returns table for approvals of reviewRequestDetails.
   * @param {ReviewRequestDetails} reviewRequestDetails
   * @return {Table}
   */
  formatTableDataApproval(reviewRequestDetails: ReviewRequestDetails): Table {
    const headData = ['Resultaat', 'Van', 'Gegeven op', 'Toelichting'];

    const bodyData = reviewRequestDetails.approvals.map((review: Review) => {
      const author = this.getAuthorName(review.author);

      const icon = review.approved ? 'done' : 'close';
      const iconColor = review.approved ? 'green' : 'red'

      const cellData: RowData = {
        cellData: {
          akkoord: {
            type: 'icon',
            label: icon,
            iconColor: iconColor
          } as ExtensiveCell,

          van: author,
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

  /**
   * Returns table for review documents.
   * @param {ReviewDocument[]} reviewDocuments
   * @return {Table}
   */
  formatTableReviewDoc(reviewDocuments: ReviewDocument[]): Table {
    const headData = ['Bestandsnaam', 'Originele versie', 'Aangepaste versie'];

    const bodyData = reviewDocuments.map((doc: ReviewDocument) => {
      return {
        cellData: {
          title: doc.bestandsnaam,

          source: {
            type: 'button',
            label: doc.sourceVersion.toString(10),
            value: doc.sourceUrl
          } as ExtensiveCell,

          advice: {
            type: 'button',
            label: doc.reviewVersion.toString(10),
            value: doc.reviewUrl
          } as ExtensiveCell,
        }
      }
    })

    return new Table(headData, bodyData);
  }

  /**
   * Returns the string representation for the author.
   * @param {Author} author
   * @return {string}
   */
  getAuthorName(author: Author): string {
    return author['fullName'] ? author['fullName'] : author['username'];
  }

  editReceivers(uuid) {
    const formData = { updateUsers: true }
    const successMessage = 'Er wordt een actie aangemaakt om de ontvangers aan te passen. Een moment geduld.'
    const errorMessage = 'Fout bij het opstarten van actie voor "Ontvangers aanpassen". Probeer het nogmaals'
    this.reviewRequestService.updateReviewRequest(uuid, formData).subscribe(res => {
      this.snackbarService.openSnackBar(successMessage, 'Sluiten', 'primary');
      this.modalService.close('adviseren-accorderen-detail-modal')
    }, error => {
      this.snackbarService.openSnackBar(errorMessage, 'Sluiten', 'warn');
    })
  }

  //
  // Events.
  //
  /**
   * Gets called when a table row is clicked.
   * @param {Object} action
   */
  tableClick(action: object): void {
    const actionType = Object.keys(action)[0];
    const endpoint = action[actionType];
    this.readDocument(endpoint).subscribe((res: ReadWriteDocument) => {
      window.open(res.magicUrl, "_blank");
    });
  }

  readDocument(endpoint): Observable<ReadWriteDocument> {
    return this.http.Post<ReadWriteDocument>(endpoint);
  }
}
