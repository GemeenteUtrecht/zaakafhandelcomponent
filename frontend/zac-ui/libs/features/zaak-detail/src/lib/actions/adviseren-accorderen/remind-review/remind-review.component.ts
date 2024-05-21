import { Component, EventEmitter, OnChanges, Input, Output, SimpleChanges } from '@angular/core';
import { ReviewRequestSummary } from '@gu/kownsl';
import { ReviewRequestsService } from '../review-requests.service';
import { SnackbarService } from '@gu/components';

/**
 * Allows user to remind a kownsl review request.
 *
 * <gu-remind-review [reviewRequestSummary]="reviewRequestSummary" (successReload)="update()"></gu-remind-review>
 */
@Component({
  selector: 'gu-remind-review',
  templateUrl: './remind-review.component.html',
  styleUrls: ['./remind-review.component.scss']
})
export class RemindReviewComponent implements OnChanges {
  @Input() reviewRequestSummary: ReviewRequestSummary;
  @Output() successReload: EventEmitter<boolean> = new EventEmitter<boolean>();

  isSubmitting: boolean;
  submitSuccess: boolean;

  constructor(
    private reviewRequestsService: ReviewRequestsService,
    private snackbarService: SnackbarService,
  ) { }

  ngOnChanges(changes: SimpleChanges): void {
    this.submitSuccess = false;
  }

  /**
   * Send POST request to remind review users
   */
  remindReview() {
    this.isSubmitting = true;
    this.reviewRequestsService.remindReviewRequest(this.reviewRequestSummary.id)
      .subscribe(() => {
        this.snackbarService.openSnackBar('Verzonden', 'Sluiten', 'primary');
        this.isSubmitting = false;
        this.successReload.emit(true);
      }, error => {
        this.reportError(error)
        this.isSubmitting = false;
      })
  }

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    const errorMessage = error.detail || 'Rappelleren van de taak is niet gelukt';
    this.snackbarService.openSnackBar(errorMessage, 'Sluiten', 'warn');
    console.error(error);
  }

}
