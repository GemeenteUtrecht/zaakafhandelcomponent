import {
  ChangeDetectorRef,
  Component,
  EventEmitter,
  Input,
  OnChanges,
  Output,
  SimpleChanges
} from '@angular/core';
import { TaskContextData } from '../../../../../models/task-context';
import { FormBuilder } from '@angular/forms';
import { Zaak } from '@gu/models';
import { AccountsService, CamundaService, ZaakService } from '@gu/services';
import { SnackbarService } from '@gu/components';
import { MatStepperIntl } from '@angular/material/stepper';
import { STEPPER_GLOBAL_OPTIONS } from '@angular/cdk/stepper';

@Component({
  selector: 'gu-start-process',
  templateUrl: './start-process.component.html',
  styleUrls: ['./start-process.component.scss'],
  providers: [
    {provide: STEPPER_GLOBAL_OPTIONS, useValue: { displayDefaultIndicatorType: false }}
  ],
})
export class StartProcessComponent implements OnChanges {
  @Input() zaak: Zaak;
  @Input() taskContextData: TaskContextData;

  @Output() successReload: EventEmitter<boolean> = new EventEmitter<boolean>();

  isSubmitting: boolean;
  errorMessage: string;

  rolesFields: any;

  propertiesFields: any;

  documentsFields: any;

  constructor(
    private fb: FormBuilder,
    private zaakService: ZaakService,
    private accountsService: AccountsService,
    private snackbarService: SnackbarService,
    private camundaService: CamundaService,
    private _matStepperIntl: MatStepperIntl,
    private cdRef: ChangeDetectorRef,
  ) { }

  //
  // Getters and setters
  //

  get rolesCount(): string {
    this._matStepperIntl.optionalLabel = this.displayCount(this.rolesFields);
    return this.displayCount(this.rolesFields);
  }

  get propertiesCount(): string {
    this._matStepperIntl.optionalLabel = this.displayCount(this.propertiesFields);
    return this.displayCount(this.propertiesFields);
  }

  get documentsCount(): string {
    return this.displayCount(this.documentsFields);
  }

  //
  // Angular lifecycle.
  //

  ngOnChanges(changes: SimpleChanges): void {
  }

  //
  // Events
  //

  submitTask(): void {
    const formData = {
      form: "zac:startProcessForm"
    }
    this.isSubmitting = true;
    this.camundaService.updateUserTask(this.taskContextData.task.id, formData)
      .subscribe(() => {
        this.isSubmitting = false
        this.successReload.emit(true)
      }, error => {
        this.errorMessage = JSON.stringify(error);
        this.reportError(error)
      })
  }

  displayCount(fieldsCount): string {
    if (fieldsCount.total === 0 || fieldsCount.submitted === fieldsCount.total) {
      return 'voltooid'
    }
    else {
      return `${fieldsCount.submitted}/${fieldsCount.total}`
    }
  }

  updateView() {
    this.cdRef.detectChanges();
  }

  //
  // Error handling.
  //

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    this.isSubmitting = false;
    this.snackbarService.openSnackBar(this.errorMessage, 'Sluiten', 'warn');
    console.error(error);
  }

}
