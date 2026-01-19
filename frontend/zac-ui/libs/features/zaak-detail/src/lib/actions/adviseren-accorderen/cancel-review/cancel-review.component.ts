import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { ReviewRequestSummary } from '@gu/kownsl';
import { ReviewRequestsService } from '../review-requests.service';
import { FieldConfiguration, SnackbarService } from '@gu/components';

/**
 * Allows user to cancel a kownsl review request.
 *
 * <gu-cancel-review [reviewRequestSummary]="reviewRequestSummary" (successReload)="update()"></gu-cancel-review>
 */
@Component({
  selector: 'gu-cancel-review',
  templateUrl: './cancel-review.component.html',
  styleUrls: ['./cancel-review.component.scss']
})
export class CancelReviewComponent {
  @Input() reviewRequestSummary: ReviewRequestSummary;
  @Output() successReload: EventEmitter<boolean> = new EventEmitter<boolean>();

  form: FieldConfiguration[] = [
    {
      label: 'Reden annulering',
      placeholder: ' ',
      name: 'lockReason',
      required: true,
    },
  ]

  isSubmitting: boolean;

  constructor(
    private reviewRequestsService: ReviewRequestsService,
    private snackbarService: SnackbarService,
  ) { }

  /**
   * Cancel review.
   */
  submitForm(formData) {
    if (this.reviewRequestSummary.canLock) {
      this.isSubmitting = true;
      this.reviewRequestsService.updateReviewRequest(this.reviewRequestSummary.id, formData).subscribe(() => {
        this.snackbarService.openSnackBar('De aanvraag is geannuleerd.', 'Sluiten', 'primary');
        this.isSubmitting = false;
        this.successReload.emit(true)
      }, error => {
        this.reportError(error)
        this.isSubmitting = false;
      })
    }
  }

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    const errorMessage = error.detail || 'Annuleren van de taak is niet gelukt';
    this.snackbarService.openSnackBar(errorMessage, 'Sluiten', 'warn');
    console.error(error);
  }

}
