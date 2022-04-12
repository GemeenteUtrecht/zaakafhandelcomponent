import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { ReviewRequestSummary } from '@gu/kownsl';
import { ReviewRequestsService } from '../review-requests.service';
import { FieldConfiguration, SnackbarService } from '@gu/components';

@Component({
  selector: 'gu-cancel-review',
  templateUrl: './cancel-review.component.html',
  styleUrls: ['./cancel-review.component.scss']
})
export class CancelReviewComponent implements OnInit {
  @Input() reviewRequestSummary: ReviewRequestSummary;
  @Output() successReload: EventEmitter<boolean> = new EventEmitter<boolean>();

  form: FieldConfiguration[];
  isSubmitting: boolean;

  constructor(
    private reviewRequestsService: ReviewRequestsService,
    private snackbarService: SnackbarService,
  ) { }

  ngOnInit(): void {
    this.form = [
      {
        label: 'Reden annulering',
        placeholder: ' ',
        name: 'lockReason',
        required: false,
      },
    ]
  }

  /**
   * Cancel review.
   */
  submitForm(formData) {
    if (this.reviewRequestSummary.canLock) {
      this.reviewRequestsService.cancelReviewRequest(this.reviewRequestSummary.id, formData).subscribe(() => {
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
    this.snackbarService.openSnackBar('Annuleren van de taak is niet gelukt', 'Sluiten', 'warn');
    console.error(error);
  }

}
