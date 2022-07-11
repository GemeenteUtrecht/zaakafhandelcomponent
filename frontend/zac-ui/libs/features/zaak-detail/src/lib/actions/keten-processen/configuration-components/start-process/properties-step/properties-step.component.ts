import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges } from '@angular/core';
import { NieuweEigenschap, Zaak } from '@gu/models';
import { BenodigdeZaakeigenschap, TaskContextData } from '../../../../../../models/task-context';
import { FormArray, FormBuilder, FormControl, FormGroup } from '@angular/forms';
import { AccountsService, ZaakService } from '@gu/services';
import { SnackbarService } from '@gu/components';

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

  startProcessPropertyForm: FormGroup;
  errorMessage: string;

  submittedProperties: number[] = [];
  submittingProperties: number[] = [];

  constructor(
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
    if (changes.taskContextData.previousValue !== this.taskContextData ) {
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
    const arr = this.taskContextData.context.benodigdeZaakeigenschappen.map(() => {
      return this.fb.control('');
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
   * Submits the selected property to the API.
   * @param i
   */
  submitProperty(i) {
    const selectedProperty = this.getPropertiesContext(i);
    this.submittingProperties.push(i)
    this.propertyControl(i).disable()

    const newCaseProperty: NieuweEigenschap = {
      naam: selectedProperty.eigenschap.naam,
      waarde: this.propertyControl(i).value,
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

        this.updateComponents.emit(true);
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
