import { Component, EventEmitter, Input, Output } from '@angular/core';
import { Task } from '@gu/models';
import { SnackbarService } from '@gu/components';
import { KetenProcessenService } from '../keten-processen.service';

/**
 * Allows user to cancel a camunda task.
 */
@Component({
  selector: 'gu-cancel-task',
  templateUrl: './cancel-task.component.html',
  styleUrls: ['./cancel-task.component.scss']
})
export class CancelTaskComponent {
  @Input() taskData: Task;
  @Output() successReload: EventEmitter<boolean> = new EventEmitter<boolean>();

  isSubmitting: boolean;

  constructor(
    private kService: KetenProcessenService,
    private snackbarService: SnackbarService
  ) { }

  /**
   * Cancel task.
   */
  cancelTask() {
    if (this.taskData.canCancelTask) {
      const formData = {task: this.taskData.id};
      this.kService.cancelTask(formData).subscribe(() => {
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
