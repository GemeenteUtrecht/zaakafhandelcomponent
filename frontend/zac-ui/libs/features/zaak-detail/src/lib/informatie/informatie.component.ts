import {Component, Input, OnInit, OnChanges} from '@angular/core';
import {InformatieService} from './informatie.service';
import {Zaak} from '@gu/models';
import {FieldConfiguration} from "../form/field";

@Component({
  selector: 'gu-informatie',
  templateUrl: './informatie.component.html',
  styleUrls: ['./informatie.component.scss']
})
export class InformatieComponent implements OnInit, OnChanges {
  @Input() bronorganisatie: string;
  @Input() identificatie: string;
  @Input() zaakData: Zaak;

  /** @type {boolean} Whether this component is loading. */
  isLoading: boolean;

  /** @type {Object[]} The properties to display as part of the form. */
  properties: Array<Object>;

  /** @type {Object[]} The confidentiality choices. */
  confidentialityChoices: Array<{ label: string, value: string }>;

  constructor(private informatieService: InformatieService) {}

  ngOnInit() {
    this.fetchConfidentialityChoices();
  }

  ngOnChanges(): void {
    this.fetchProperties();
  };

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
   * Fetches the properties to show (read
   */
  fetchProperties() {
    this.isLoading = true;
    this.informatieService.getProperties(this.bronorganisatie, this.identificatie).subscribe(

      (data) => {
        this.properties = data;
        this.isLoading = false;

      }, (error) => {
        console.error(error);
        this.isLoading = false;
      })
  }

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
        value: this.zaakData.vertrouwelijkheidaanduiding,
        choices: this.confidentialityChoices,
      },
      {
        label: 'Omschrijving',
        name: 'omschrijving',
        placeholder: 'Geen omschrijving',
        value: this.zaakData.omschrijving,
      },
      {
        label: 'Toelichting',
        name: 'toelichting',
        required: false,
        value: this.zaakData.toelichting,
      },
      {
        label: 'reden',
        value: '',
        writeonly: true,
      },
    ];
  }

  /**
   * Returns the field configurations for the (readonly) properties.
   */
  get propertyFieldConfigurations(): Array<FieldConfiguration> {
    return this.properties.map((property:{eigenschap: {naam: string}, value: string}) => ({
      label: property.eigenschap.naam,
      readonly: true,
      value: property.value,
    }))
  }

  /***
   * Submits the form.
   * @param {Object} data
   */
  submitForm(data) {
    this.isLoading = true
    this.informatieService.patchCaseDetails(this.bronorganisatie, this.identificatie, data).subscribe(

      () => {
        this.isLoading = false
      },

      (error) => {
        console.error(error);
        this.isLoading = false
      }
    );
  }
}
