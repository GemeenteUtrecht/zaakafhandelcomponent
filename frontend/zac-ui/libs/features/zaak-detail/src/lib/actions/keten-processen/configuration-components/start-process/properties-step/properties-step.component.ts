import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges } from '@angular/core';
import { NieuweEigenschap, Zaak } from '@gu/models';
import { BenodigdeZaakeigenschap, TaskContextData } from '../../../../../../models/task-context';
import { FormArray, FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { AccountsService, ZaakService } from '@gu/services';
import { SnackbarService } from '@gu/components';
import { DatePipe } from '@angular/common';

/**
 * This component allows the user to configure
 * case properties to start a camunda process.
 */
@Component({
  selector: 'gu-properties-step',
  templateUrl: './properties-step.component.html',
  styleUrls: ['../start-process.component.scss']
})
export class PropertiesStepComponent implements OnChanges {
  @Input() zaak: Zaak;
  @Input() taskContextData: TaskContextData;

  @Output() submittedFields: EventEmitter<any> = new EventEmitter<any>();
  @Output() updateComponents: EventEmitter<boolean> = new EventEmitter<boolean>();

  @Input() startProcessPropertyForm: FormGroup;

  errorMessage: string;

  submittedProperties: number[] = [];
  submittingProperties: number[] = [];

  constructor(
    private datePipe: DatePipe,
    private fb: FormBuilder,
    private zaakService: ZaakService,
    private accountsService: AccountsService,
    private snackbarService: SnackbarService,
  ) { }

  //
  // Getters / setters.
  //

  get propertiesControl(): FormArray {
    return this.startProcessPropertyForm.get('properties') as FormArray;
  };

  propertyControl(i): FormControl {
    return this.propertiesControl.at(i) as FormControl;
  }

  //
  // Angular lifecycle.
  //

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.taskContextData) {
      if (changes.taskContextData.previousValue !== this.taskContextData || changes.taskContextData?.firstChange) {
        this.taskContextData.context.benodigdeZaakeigenschappen.sort((a, b) => a.order - b.order);
        this.startProcessPropertyForm = this.fb.group({
          properties: this.addPropertyControls()
        })
        this.submittedProperties = [];
        this.submittingProperties = [];
        this.submittedFields.emit({
          submitted: 0,
          total: this.propertiesControl.controls.length,
          hasValidForm: this.startProcessPropertyForm.valid
        })
      }
    }
  }

  //
  // Context.
  //

  /**
   * Returns the context for the given index
   * @param i
   * @returns {BenodigdeZaakeigenschap}
   */
  getPropertiesContext(i): BenodigdeZaakeigenschap {
    return this.taskContextData.context.benodigdeZaakeigenschappen[i];
  }

  /**
   * Creates form controls.
   * @returns {FormArray}
   */
  addPropertyControls(): FormArray {
    const arr = this.taskContextData.context.benodigdeZaakeigenschappen.map(prop => {
      if (prop.required) {
        return this.fb.control('', Validators.required);
      } else {
        return this.fb.control('');
      }
    });
    return this.fb.array(arr);
  }

  /**
   * Checks if property is already submitted.
   * @param i
   * @returns {boolean}
   */
  isSubmittedProperty(i) {
    return this.submittedProperties.indexOf(i) !== -1;
  }

  //
  // Events
  //

  /**
   * Loop and post properties
   */
  submitProperties() {
    this.propertiesControl.controls.forEach((control, i) => {
      if (control.value) {
        this.postProperty(i);
      }
    })
  }


  /**
   * Submits the selected property to the API.
   * @param i
   */
  postProperty(i) {
    this.submittingProperties.push(i);

    const selectedProperty = this.getPropertiesContext(i);
    const selectedValue = selectedProperty.eigenschap.specificatie.formaat === ('datum' || 'datum_tijd')
      ? this.datePipe.transform(this.propertyControl(i).value, "yyyy-MM-dd")
      : this.propertyControl(i).value;

    const newCaseProperty: NieuweEigenschap = {
      naam: selectedProperty.eigenschap.naam,
      waarde: selectedValue,
      zaakUrl: this.zaak.url
    };

    this.zaakService.createCaseProperty(newCaseProperty)
      .subscribe(() => {
        this.submittingProperties = this.submittingProperties.filter(index => index !== i);
        this.submittedProperties.push(i);

        // Emit the total submitted properties to parent
        this.submittedFields.emit({
          submitted: this.submittedProperties.length,
          total: this.propertiesControl.controls.length,
          hasValidForm: this.startProcessPropertyForm.valid
        })

        if (this.submittingProperties.length === 0) {
          this.updateComponents.emit(true);
        }
        this.propertyControl(i).disable()
      }, error => {
        this.submittingProperties = this.submittingProperties.filter(index => index !== i);
        this.propertyControl(i).enable();
        this.errorMessage = 'Het aanmaken van de eigenschap is mislukt.'
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
