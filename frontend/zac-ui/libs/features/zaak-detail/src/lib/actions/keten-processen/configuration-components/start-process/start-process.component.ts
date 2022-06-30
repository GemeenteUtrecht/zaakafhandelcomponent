import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges } from '@angular/core';
import { TaskContextData } from '../../../../../models/task-context';
import { FormBuilder } from '@angular/forms';
import { Zaak } from '@gu/models';
import { AccountsService, CamundaService, ZaakService } from '@gu/services';
import { SnackbarService } from '@gu/components';

@Component({
  selector: 'gu-start-process',
  templateUrl: './start-process.component.html',
  styleUrls: ['./start-process.component.scss']
})
export class StartProcessComponent implements OnChanges {
  @Input() zaak: Zaak;
  @Input() taskContextData: TaskContextData;

  @Output() successReload: EventEmitter<boolean> = new EventEmitter<boolean>();

  isSubmitting: boolean;
  errorMessage: string;

  constructor(
    private fb: FormBuilder,
    private zaakService: ZaakService,
    private accountsService: AccountsService,
    private snackbarService: SnackbarService,
    private camundaService: CamundaService
  ) { }

  //
  // Angular lifecycle.
  //

  ngOnChanges(changes: SimpleChanges): void {
  }

  //
  // Events
  //

  submitTask() {
    const formData = {
      form: "zac:startProcessForm"
    }
    this.isSubmitting = true;
    this.camundaService.updateUserTask(this.taskContextData.task.id, formData)
      .subscribe(() => {
        this.isSubmitting = false
        this.successReload.emit(true)
      }, error => {
        this.errorMessage = "Het is niet gelukt om de gegevens te versturen."
        this.reportError(error)
      })
  }

  //
  // Error handling.
  //

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    this.snackbarService.openSnackBar(this.errorMessage, 'Sluiten', 'warn');
    console.error(error);
  }

}
