import {Component, Input, OnInit, OnChanges} from '@angular/core';
import {Zaak} from '@gu/models';
import {FieldConfiguration} from '../form/field';
import {InformatieService} from './informatie.service';
import {ZaakService} from "@gu/services";

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

  /** @type {boolean} Whether this component is loading. */
  isLoading: boolean;

  /** @type {Object[]} The confidentiality choices. */
  confidentialityChoices: Array<{ label: string, value: string }>;

  /** @type {Object[]} The properties to display as part of the form. */
  properties: Array<Object>;

  /** @type {Zaak} The zaak object. */
  zaak: Zaak = null;

  constructor(
    private informatieService: InformatieService,
    private zaakService: ZaakService,
  ) {
  }

  //
  // Getters / setters.
  //

  /**
   * Returns the field configurations for the form..
   */
  get form(): Array<FieldConfiguration> {
    return [...this.caseDetailsFieldConfigurations, ...this.propertyFieldConfigurations];
  }

  /**
   * Returns the field configurations for the (editable) case details.
   */
  get caseDetailsFieldConfigurations(): Array<FieldConfiguration> {
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
        value: this.zaak.omschrijving,
      },
      {
        label: 'Toelichting',
        placeholder: ' ',
        name: 'toelichting',
        required: false,
        value: this.zaak.toelichting,
      },
      {
        label: 'reden',
        placeholder: 'Reden',
        value: '',
        writeonly: true,
      },
    ];
  }

  /**
   * Returns the field configurations for the (readonly) properties.
   */
  get propertyFieldConfigurations(): Array<FieldConfiguration> {
    return this.properties.map((property: { eigenschap: { naam: string }, value: string }) => ({
      label: property.eigenschap.naam,
      readonly: true,
      value: property.value,
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
    this.isLoading = true;
    this.zaakService.listCaseProperties(this.bronorganisatie, this.identificatie).subscribe(
      (data) => {
        this.properties = data;
        this.isLoading = false;

      }, (error) => {
        console.error(error);
        this.isLoading = false;
      })
  }

  /**
   * Fetches the confidentiality choices
   */
  fetchConfidentialityChoices() {
    this.isLoading = true;

    this.informatieService.getConfidentiality().subscribe(
      (data) => {
        this.confidentialityChoices = data;
        this.isLoading = false;
      },
      (error) => {
        console.error(error);
        this.isLoading = false;
      })
  }

  /**
   * Updates this.zaakData with latest values from API.
   */
  fetchZaak() {
    this.isLoading = true;
    this.zaakService.retrieveCaseDetails(this.bronorganisatie, this.identificatie).subscribe(
      (zaak: Zaak) => {
        this.zaak = zaak;
        this.isLoading = false;
      },
      (error: any) => {
        console.error(error);
        this.isLoading = false;
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
    this.isLoading = true
    this.zaakService.updateCaseDetails(this.bronorganisatie, this.identificatie, data).subscribe(
      () => {
        this.fetchZaak();
        this.isLoading = false
      },

      (error: any) => {
        console.error(error);
        this.isLoading = false
      }
    );
  }
}
