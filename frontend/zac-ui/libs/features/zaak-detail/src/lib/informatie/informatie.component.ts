import {Component, Input, OnInit, OnChanges} from '@angular/core';
import {EigenschapWaarde, Zaak} from '@gu/models';
import {FieldConfiguration, SnackbarService} from '@gu/components';
import {InformatieService} from './informatie.service';
import {ZaakService} from '@gu/services';

/**
 * <gu-informatie [bronorganisatie]="bronorganisatie" [identificatie]="identificatie"></gu-informatie>
 *
 * Shows case (zaak) informatie and allows inline editing.
 *
 * Requires bronorganisatie: string input to identify the organisation.
 * Requires identificatie: string input to identify the case (zaak).
 */
@Component({
  selector: 'gu-informatie',
  templateUrl: './informatie.component.html',
  styleUrls: ['./informatie.component.scss']
})
export class InformatieComponent implements OnInit, OnChanges {
  @Input() bronorganisatie: string;
  @Input() identificatie: string;

  readonly errorMessage = 'Er is een fout opgetreden bij het laden van zaakinformatie.'

  /** @type {boolean} Whether the case API is loading. */
  isCaseAPILoading: boolean;

  /** @type {number} Whether the property API is loading. */
  isPropertyAPILoading = 0;

  /** @type {Object[]} The confidentiality choices. */
  confidentialityChoices: Array<{ label: string, value: string }>;

  /** @type {Object[]} The properties to display as part of the form. */
  properties: EigenschapWaarde[];

  /** @type {Zaak} The zaak object. */
  zaak: Zaak = null;

  /**
   * Constructor method.
   * @param {InformatieService} informatieService
   * @param {SnackbarService} snackbarService
   * @param {ZaakService} zaakService
   */
  constructor(
    private informatieService: InformatieService,
    private snackbarService: SnackbarService,
    private zaakService: ZaakService,
  ) {
  }

  //
  // Getters / setters.
  //

  /**
   * Returns the field configurations for the form..
   */
  get form(): FieldConfiguration[] {
    return [
      ...this.caseDetailsFieldConfigurations,
      ...this.propertyFieldConfigurations,
      {
        label: 'reden',
        placeholder: 'Reden',
        value: '',
        required: true,
        writeonly: true,
      }
    ];
  }

  /**
   * Returns the field configurations for the (editable) case details.
   */
  get caseDetailsFieldConfigurations(): FieldConfiguration[] {
    return [
      {
        label: 'Identificatie',
        name: 'identificatie',
        value: this.identificatie,
        readonly: true,
      },
      {
        label: 'Vertrouwelijkheidaanduiding',
        name: 'vertrouwelijkheidaanduiding',
        value: this.zaak.vertrouwelijkheidaanduiding,
        choices: this.confidentialityChoices,
      },
      {
        label: 'Omschrijving',
        name: 'omschrijving',
        placeholder: 'Geen omschrijving',
        required: true,
        value: this.zaak.omschrijving,
      },
      {
        label: 'Toelichting',
        placeholder: ' ',
        name: 'toelichting',
        required: true,
        value: this.zaak.toelichting,
      },
    ];
  }

  /**
   * @type {boolean} Whether this component is loading.
   * */
  get isLoading(): boolean {
    return this.isCaseAPILoading || Boolean(this.isPropertyAPILoading);
  }

  /**
   * Returns the field configurations for the (readonly) properties.
   */
  get propertyFieldConfigurations(): FieldConfiguration[] {
    return this.properties.map((property: EigenschapWaarde) => ({
      label: property.eigenschap.naam,
      readonly: false,
      value: String(property.value),
    }))
  }

  //
  // Angular lifecycle.
  //

  /**
   * A lifecycle hook that is called after Angular has initialized all data-bound properties of a directive. Define an
   * ngOnInit() method to handle any additional initialization tasks.
   */
  ngOnInit() {
    this.fetchConfidentialityChoices();
  }

  /**
   * A lifecycle hook that is called when any data-bound property of a directive changes. Define an ngOnChanges() method
   * to handle the changes.
   */
  ngOnChanges(): void {
    this.getContextData();
  };

  //
  // Context.
  //

  /**
   * Fetches the properties to show in the form.
   */
  getContextData() {
    this.fetchZaak();
    this.isCaseAPILoading = true;
    this.zaakService.listCaseProperties(this.bronorganisatie, this.identificatie).subscribe(
      (data) => {
        this.properties = data;
        this.isCaseAPILoading = false;

      }, (error) => {
        console.error(error);
        this.isCaseAPILoading = false;
      })
  }

  /**
   * Fetches the confidentiality choices
   */
  fetchConfidentialityChoices() {
    this.isCaseAPILoading = true;

    this.informatieService.getConfidentiality().subscribe(
      (data) => {
        this.confidentialityChoices = data;
        this.isCaseAPILoading = false;
      },
      (error) => {
        console.error(error);
        this.isCaseAPILoading = false;
      })
  }

  /**
   * Updates this.zaakData with latest values from API.
   */
  fetchZaak() {
    this.isCaseAPILoading = true;
    this.zaakService.retrieveCaseDetails(this.bronorganisatie, this.identificatie).subscribe(
      (zaak: Zaak) => {
        this.zaak = zaak;
        this.isCaseAPILoading = false;
      },
      (error: any) => {
        console.error(error);
        this.isCaseAPILoading = false;
      }
    );
  }

  //
  // Events.
  //

  /***
   * Submits the form.
   * @param {Object} data
   */
  submitForm(data) {
    const propertyKeys = this.properties.map((propertyValue: EigenschapWaarde) => propertyValue.eigenschap.naam)
    const propertyData = Object.entries(data)
      .filter(([key]) => propertyKeys.indexOf(key) > -1)
      .reduce((acc, [key, value]) => ({...acc, [key]: value}), {});


    const zaakData = Object.entries(data)
      .filter(([key]) => propertyKeys.indexOf(key) === -1)
      .reduce((acc, [key, value]) => ({...acc, [key]: value}), {});

    this.submitProperties(propertyData);
    this.submitZaak(zaakData);
  }


  /**
   * Submits the properties.
   * @param {Object} data
   */
  submitProperties(data: Object): void {
    this.isPropertyAPILoading = Object.entries(data).reduce((acc, [key, value], index) => {
      const property = this.properties.find((propertyValue: EigenschapWaarde) => propertyValue.eigenschap.naam === key)
      property.value = value;

      this.zaakService.updateCaseProperty(property).subscribe(
        () => {},
        this.reportError.bind(this),
        () => this.isPropertyAPILoading--,
      );

      return acc + 1;
    }, 0);
  }

  /**
   * Submits the zaak.
   * @param {Object} data
   */
  submitZaak(data: Object): void {
    this.isCaseAPILoading = true;
    this.zaakService.updateCaseDetails(this.bronorganisatie, this.identificatie, data).subscribe(
      () => {
        this.fetchZaak();
        this.isCaseAPILoading = false
      },
      this.reportError.bind(this),
    );
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
