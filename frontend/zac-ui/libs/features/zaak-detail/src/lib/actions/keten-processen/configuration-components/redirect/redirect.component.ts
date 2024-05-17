import { Component, EventEmitter, Input, Output } from '@angular/core';
import { TaskContextData } from '../../../../../models/task-context';
import { ApplicationHttpClient } from '@gu/services';
import { UntypedFormBuilder } from '@angular/forms';
import { KetenProcessenService } from '../../keten-processen.service';
import { ModalService } from '@gu/components';

@Component({
  selector: 'gu-redirect',
  templateUrl: './redirect.component.html',
  styleUrls: ['../configuration-components.scss']
})
export class RedirectComponent {
  /**
   * Allows the user to complete an external opened task
   * from the parent component by submitting the task id.
   */

  @Input() taskContextData: TaskContextData;
  @Input() target: '_blank' | '_self';

  @Output() successReload: EventEmitter<boolean> = new EventEmitter<boolean>();

  isSubmitting: boolean;
  submitSuccess: boolean;
  submitHasError: boolean;
  submitErrorMessage: string;

  constructor(
    private http: ApplicationHttpClient,
    private fb: UntypedFormBuilder,
    private ketenProcessenService: KetenProcessenService,
    private modalService: ModalService
  ) { }

  submitForm() {
    this.isSubmitting = true;
    const formData = {
      form: this.taskContextData.form
    }
    this.ketenProcessenService.putTaskData(this.taskContextData.task.id, formData).subscribe(() => {
      this.isSubmitting = false;
      this.submitSuccess = true;
      this.successReload.emit(true);

      this.modalService.close('ketenprocessenModal');
    }, res => {
      this.isSubmitting = false;
      this.submitErrorMessage = res.error.detail ? res.error.detail : "Er is een fout opgetreden";
      this.submitHasError = true;
    })
  }

}
