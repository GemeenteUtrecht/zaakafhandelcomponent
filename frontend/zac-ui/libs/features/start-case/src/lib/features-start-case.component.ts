import {Component, OnInit} from '@angular/core';
import { CreateCase, MetaZaaktypeResult, Zaak } from '@gu/models';
import { Choice, FieldConfiguration, SnackbarService } from '@gu/components';
import { CamundaService, MetaService, ZaakService } from '@gu/services';
import { delay, retryWhen, take } from 'rxjs/operators';

@Component({
  selector: 'gu-features-start-case',
  templateUrl: './features-start-case.component.html',
  styleUrls: ['./features-start-case.component.scss'],
})
export class FeaturesStartCaseComponent implements OnInit {
  caseTypes: MetaZaaktypeResult[];
  caseTypeChoices: Choice[];
  form: FieldConfiguration[] = null;

  isLoading: boolean;
  isSubmitting: boolean;
  errorMessage: string;

  constructor(
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
    this.isLoading = true;
    this.metaService.getCaseTypes().subscribe(
      (data) => {
        this.isLoading = false;
        this.caseTypes = data.results;
        this.caseTypeChoices = this.caseTypes.map( type => {
          return {
            label: `${type.omschrijving}: ${type.catalogus.domein}`,
            value: `${type.omschrijving},${type.catalogus.url}`
          }
        })
        console.log(this.caseTypeChoices);
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
   * @param formData
   */
  createCase(formData) {
    const zaaktypeOmschrijving = formData.zaaktype.split(',')[0];
    const zaaktypeUrl = formData.zaaktype.split(',')[1];

    const createCaseData: CreateCase = {
      zaaktypeOmschrijving: zaaktypeOmschrijving,
      zaaktypeCatalogus: zaaktypeUrl,
      zaakDetails: {
        omschrijving: formData.omschrijving,
        toelichting: formData.toelichting
      }
    }

    this.zaakService.createCase(createCaseData)
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
      .pipe(
        retryWhen(errors => errors.pipe(delay(2000), take(5)))
      )
      .subscribe(processInstanceCase => {
        this.zaakService.navigateToCaseActions({
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
    this.isLoading = false;
    this.isSubmitting = false;
    this.snackbarService.openSnackBar(this.errorMessage, 'Sluiten', 'warn');
    console.error(error);
  }
}
