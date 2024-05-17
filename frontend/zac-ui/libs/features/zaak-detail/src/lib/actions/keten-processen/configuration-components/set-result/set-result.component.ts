import { Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges } from '@angular/core';
import { FormField, TaskContextData } from '../../../../../models/task-context';
import { UntypedFormBuilder, UntypedFormControl, UntypedFormGroup, Validators } from '@angular/forms';
import { KetenProcessenService } from '../../keten-processen.service';
import { Choice, FieldConfiguration, ModalService } from '@gu/components';

@Component({
  selector: 'gu-set-result',
  templateUrl: './set-result.component.html',
  styleUrls: ['../configuration-components.scss']
})
export class SetResultComponent implements OnChanges {
  @Input() taskContextData: TaskContextData;

  @Output() successReload: EventEmitter<boolean> = new EventEmitter<boolean>();

  setResultForm: UntypedFormGroup;
  formItems: Choice[];
  formData: any;

  isSubmitting: boolean;
  submitSuccess: boolean;
  submitHasError: boolean;
  submitErrorMessage: string;

  showCloseCaseConfirmation = false;

  constructor(
    private fb: UntypedFormBuilder,
    private ketenProcessenService: KetenProcessenService,
    private modalService: ModalService,
  ) { }

  //
  // Getters / setters.
  //

  get resultControl(): UntypedFormControl {
    return this.setResultForm.get('resultaat') as UntypedFormControl;
  };


  ngOnChanges(changes: SimpleChanges): void {
    if (changes.taskContextData.previousValue !== this.taskContextData ) {
      this.setResultForm = this.fb.group({
        resultaat: ['', Validators.required]
      })
      this.formItems = this.taskContextData.context.resultaattypen.map(type => ({label: type.omschrijving, value: type.omschrijving}));
    }
  }

  /**
   * Checks if current case has opens tasks
   */
  checkSubmitForm() {
    const hasOpenTasks =
      this.taskContextData.context.taken.length > 1 ||
      this.taskContextData.context.activiteiten ||
      this.taskContextData.context.checklistVragen ||
      this.taskContextData.context.verzoeken;
    if (hasOpenTasks) {
      this.showCloseCaseConfirmation = true;
      this.resultControl.disable();
    } else {
      this.putForm();
    }
  }

  /**
   * PUT request.
   */
  putForm() {
    this.isSubmitting = true;

    const formData = {
      form: this.taskContextData.form,
      resultaat: this.resultControl.value
    }

    this.ketenProcessenService.putTaskData(this.taskContextData.task.id, formData).subscribe(() => {
      // Delay reload to make sure camunda has processed the task.
      setTimeout(() => {
        this.isSubmitting = false;
        this.submitSuccess = true;
        this.successReload.emit(true);

        this.modalService.close('ketenprocessenModal');
        document.location.reload()
      }, 7000)
    }, res => {
      this.isSubmitting = false;
      this.submitErrorMessage = res.error.detail ? res.error.detail : "Er is een fout opgetreden";
      this.submitHasError = true;
    })
  }
}
