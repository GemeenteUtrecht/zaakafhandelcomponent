import { Component, OnInit } from '@angular/core';
import { CamundaService, MetaService, ZaakService } from '@gu/services';
import { CreateCase, MetaZaaktypeResult, ProcessInstanceCase, Zaak } from '@gu/models';
import { Choice, FieldConfiguration, SnackbarService } from '@gu/components';
import { CreateCaseService } from './create-case.service';

@Component({
  selector: 'gu-create-case',
  templateUrl: './create-case.component.html',
  styleUrls: ['./create-case.component.scss']
})
export class CreateCaseComponent implements OnInit {

  caseTypes: MetaZaaktypeResult[];
  caseTypeChoices: Choice[];
  form: FieldConfiguration[] = null;

  isSubmitting: boolean;
  errorMessage: string;

  constructor(
    private createCaseService: CreateCaseService,
    private metaService: MetaService,
    private camundaService: CamundaService,
    private zaakService: ZaakService,
    private snackbarService: SnackbarService
  ) { }


  //
  // Angular lifecycle.
  //

  ngOnInit(): void {
    this.getContextData();
  }

  /**
   * Get context
   */
  getContextData(): void {
    this.metaService.getCaseTypes().subscribe(
      (data) => {
        this.caseTypes = data.results;
        this.caseTypeChoices = this.caseTypes.map( type => {
          return {
            label: type.omschrijving,
            value: type.catalogus,
          }
        })
        this.form = this.getForm();
      }, (error) => console.error(error),
    );
  }

  /**
   * Returns the field configurations for the form.
   * @param {Zaak} zaak If given, preselect zaak.
   */
  getForm(zaak: Zaak = null): FieldConfiguration[] {
    return [
      {
        label: 'Zaaktype',
        name: 'zaaktype',
        required: true,
        choices: this.caseTypeChoices
      },
      {
        label: 'Zaakomschrijving',
        name: 'omschrijving',
        required: true,
        value: '',
      },
      {
        label: 'Toelichting',
        name: 'toelichting',
        required: false,
        value: '',
      },
    ]
  }

  /**
   * Create a new case.
   * @param {CreateCase} formData
   */
  createCase(formData: CreateCase) {
    this.zaakService.createCase(formData)
      .subscribe(processInstance => {
        this.getCaseUrlForProcessInstance(processInstance.instanceId);
      }, error => {
        this.errorMessage = 'Het aanmaken van de zaak is mislukt. Probeer het nogmaals.'
        this.reportError(error)
      })
  }

  /**
   * Retrieve case details of the newly created case.
   * @param processInstanceId
   */
  getCaseUrlForProcessInstance(processInstanceId) {
    this.camundaService.getCaseUrlForProcessInstance(processInstanceId)
      .subscribe(processInstanceCase => {
        this.zaakService.navigateToCase({
          bronorganisatie: processInstanceCase.bronorganisatie,
          identificatie: processInstanceCase.identificatie
        })
      }, error => {
        this.errorMessage = 'De aangemaakte zaak kan niet worden gevonden.'
        this.reportError(error)
      })
  }

  //
  // Events.
  //

  /**
   * Cancel review.
   */
  submitForm(formData: CreateCase) {
    this.isSubmitting = true;
    this.createCase(formData);
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
