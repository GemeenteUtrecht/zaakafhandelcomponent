import {Injectable} from '@angular/core';
import {Observable} from 'rxjs';
import {ReviewRequestDetails, ReviewRequestSummary} from '@gu/kownsl';
import {ApplicationHttpClient} from '@gu/services';
import {CachedObservableMethod} from '@gu/utils';

export interface ReviewRequestStatus {
  icon: string,
  iconColor: string,
  label: string,
  value: string,
}

export const REVIEW_REQUEST_STATUSES: { [status: string]: ReviewRequestStatus } = {
  APPROVED: {
    icon: 'done',
    iconColor: 'green',
    label: 'Akkoord',
    value: 'Akkoord',  // As in API response.
  },

  NOT_APPROVED: {
    icon: 'close',
    iconColor: 'red',
    label: 'Niet akkoord',
    value: 'Niet akkoord',  // As in API response.
  },

  PENDING: {
    icon: 'timer',
    iconColor: 'orange',
    label: 'In afwachting',
    value: 'pending',
  },

  LOADING: {  // API loading.
    icon: 'cached',
    iconColor: 'gray',
    label: '…',
    value: null,
  }
}


@Injectable({
  providedIn: 'root'
})
export class ReviewRequestsService {

  constructor(private http: ApplicationHttpClient) {
  }

  /**
   * Returns whether all advice/approval requests are are completed.
   * @param {ReviewRequestSummary} reviewRequest
   * @return {boolean}
   */
  isReviewRequestCompleted(reviewRequest: ReviewRequestSummary): boolean {
    return reviewRequest.completed === reviewRequest.numAssignedUsers;
  }

  /**
   * Returns whether no advice/approval requests are completed.
   * @param {ReviewRequestSummary} reviewRequest
   * @return {boolean}
   */
  isReviewRequestPristine(reviewRequest: ReviewRequestSummary): boolean {
    return reviewRequest.completed < 1;
  }

  /**
   * Returns what icon should be used for this review request by reviewRequestSummary and reviewRequestDetails.
   * @param {ReviewRequestSummary} reviewRequestSummary
   * @param {ReviewRequestDetails} reviewRequestDetails
   * @return {string[]} Array of string containing two values: icon name and icon color.
   */
  getReviewRequestIcon(reviewRequestSummary: ReviewRequestSummary, reviewRequestDetails: ReviewRequestDetails): string[] {
    const reviewRequestStatus = this.getReviewRequestStatus(reviewRequestSummary, reviewRequestDetails);
    return [reviewRequestStatus.icon, reviewRequestStatus.iconColor];
  }

  /**
   * Returns the ReviewRequestStatus for the review request based on both reviewRequestSummary and reviewRequestDetails.
   * @param {ReviewRequestSummary} reviewRequestSummary
   * @param {ReviewRequestDetails} reviewRequestDetails
   * @return {ReviewRequestStatus}
   */
  getReviewRequestStatus(reviewRequestSummary: ReviewRequestSummary, reviewRequestDetails: ReviewRequestDetails): ReviewRequestStatus {
    const responses = reviewRequestDetails?.approvals || reviewRequestDetails?.advices;

    // No responses.
    if (this.isReviewRequestPristine(reviewRequestSummary)) {
      return REVIEW_REQUEST_STATUSES.PENDING;
    }

    // Details not yet loaded.
    if (!reviewRequestDetails) {
      return REVIEW_REQUEST_STATUSES.LOADING;
    }

    // Whether all approved.
    const isApproved = this.isReviewRequestCompleted(reviewRequestSummary) &&
      responses.length &&
      responses.every(a => {
        if(reviewRequestSummary.reviewType === 'approval') {
          return String(a.status).toLowerCase() === REVIEW_REQUEST_STATUSES.APPROVED.value.toLowerCase();
        }
        return true;
      });

    // Whether one or or more did not approve.
    const isNotApproved = responses.length &&
      responses.some(a => {
        if(reviewRequestSummary.reviewType === 'approval') {
          return String(a.status).toLowerCase() === REVIEW_REQUEST_STATUSES.NOT_APPROVED.value.toLowerCase();
        }
      });

    if (isApproved) {
      return REVIEW_REQUEST_STATUSES.APPROVED;
    } else if (isNotApproved) {
      return REVIEW_REQUEST_STATUSES.NOT_APPROVED;
    } else {
      return REVIEW_REQUEST_STATUSES.PENDING;  // One but not all approved.
    }
  }

  /**
   * Returns a Date object (or null) for the latest update of this review request.
   * @param {ReviewRequestDetails} reviewRequestDetails
   * @return {Date|null}
   */
  getReviewRequestLastUpdate(reviewRequestDetails: ReviewRequestDetails): Date {
    const responses = reviewRequestDetails?.approvals || reviewRequestDetails?.advices;

    if (!reviewRequestDetails || responses.length < 1) {
      return null;
    }

    const mostRecentAdvice = [...responses]
      .sort((a, b) => new Date(b.created).getTime() - new Date(a.created).getTime())
      [0];

    return new Date(mostRecentAdvice.created);
  }

  @CachedObservableMethod('ReviewRequestsService.listReviewRequestSummariesForCase')
  listReviewRequestSummariesForCase(bronorganisatie: string, identificatie: string): Observable<ReviewRequestSummary[]> {
    const endpoint = `/api/kownsl/zaak-review-requests/${bronorganisatie}/${identificatie}/summary`;
    return this.http.Get<ReviewRequestSummary[]>(endpoint);
  }

  retrieveReviewRequestDetails(requestUuid: string): Observable<ReviewRequestDetails> {
    const endpoint = encodeURI(`/api/kownsl/zaak-review-requests/${requestUuid}/detail`);
    return this.http.Get<ReviewRequestDetails>(endpoint);
  }

  /**
   * Calls retrieveReviewRequestDetails() for every requestUuid in requestUuids.
   * Subscribe.next() is called once for every result.
   * @param {string[]} requestUuids
   * @return {Observable}
   */
  retrieveReviewRequestDetailsBatch(requestUuids: string[]): Observable<ReviewRequestDetails> {
    return new Observable(((subscriber) => {
      requestUuids.forEach((requestUuid) => {
        const endpoint = encodeURI(`/api/kownsl/zaak-review-requests/${requestUuid}/detail`);

        this.http.Get<ReviewRequestDetails>(endpoint).subscribe(
          (reviewRequestDetails) => subscriber.next(reviewRequestDetails),
          (err) => subscriber.error(err),
        )
      });
    }));
  }
}
