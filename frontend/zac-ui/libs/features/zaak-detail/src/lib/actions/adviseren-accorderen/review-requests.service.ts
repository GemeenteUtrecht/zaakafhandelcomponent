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
    icon: 'check_circle',
    iconColor: 'green',
    label: 'Akkoord',
    value: 'Akkoord',
  },

  NOT_APPROVED: {
    icon: 'cancel',
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

  CANCELED: {
    icon: 'cancel',
    iconColor: 'red',
    label: 'Geannuleerd',
    value: 'Geannuleerd',
  },

  ADVICE_COMPLETE: {
    icon: 'check_circle',
    iconColor: 'green',
    label: 'Afgehandeld',
    value: 'Afgehandeld',
  }
}


@Injectable({
  providedIn: 'root'
})
export class ReviewRequestsService {

  constructor(private http: ApplicationHttpClient) {
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
    switch (reviewRequestSummary.status) {
      case 'approved':
        return REVIEW_REQUEST_STATUSES.APPROVED
      case 'not_approved':
        return REVIEW_REQUEST_STATUSES.NOT_APPROVED
      case 'pending':
        return REVIEW_REQUEST_STATUSES.PENDING
      case 'canceled':
        return REVIEW_REQUEST_STATUSES.CANCELED
      case 'completed':
        return REVIEW_REQUEST_STATUSES.ADVICE_COMPLETE
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
   * Update review request.
   * @param {string} requestUuid
   * @param {object} formData
   */
  updateReviewRequest(requestUuid: string, formData: any) {
    const endpoint = encodeURI(`/api/kownsl/zaak-review-requests/${requestUuid}/detail`);
    return this.http.Patch<ReviewRequestDetails>(endpoint, formData);
  }

  /**
   * Remind review request.
   * @param {string} requestUuid
   */
  remindReviewRequest(requestUuid: string) {
    const endpoint = encodeURI(`/api/kownsl/zaak-review-requests/${requestUuid}/reminder`);
    return this.http.Post<any>(endpoint);
  }

}
