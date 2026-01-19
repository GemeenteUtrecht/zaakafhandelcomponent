import {Component, Input, OnChanges, OnInit} from '@angular/core';
import {FieldConfiguration, SnackbarService} from '@gu/components';
import {EigenschapWaarde, NieuweEigenschap, Zaak, ZaaktypeEigenschap} from '@gu/models';
import {MetaService, ZaakService} from '@gu/services';
import {SearchService} from '../../../../../search/src/lib/search.service';

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
  /** @type {Zaak} The zaak object. */
  @Input() zaak: Zaak;

  readonly errorMessage = 'Er is een fout opgetreden bij het laden van zaakinformatie.'

  /** @type {boolean} Whether the case API is loading. */
  isCaseAPILoading: boolean;

  /** @type {number} Whether the property API is loading. */
  isPropertyAPILoading = 0;

  /** @type {number} Whether the property API is loading. */
  isCreatePropertyAPILoading = 0;

  /** @type {Object[]} The confidentiality choices. */
  confidentialityChoices: Array<{ label: string, value: string }>;

  /** @type {Object[]} The properties to display as part of the form. */
  properties: EigenschapWaarde[];

  /** @type {ZaaktypeEigenschap[]} The zaaktype eigenschappen for the zaak. */
  zaaktypeEigenschappen: ZaaktypeEigenschap[];

  /** @type {string} Link to case in Tezza. */
  tezzaLink: string;

  /**
   * Constructor method.
   * @param metaService
   * @param {SearchService} searchService
   * @param {SnackbarService} snackbarService
   * @param {ZaakService} zaakService
   */
  constructor(
    private metaService: MetaService,
    private searchService: SearchService,
    private snackbarService: SnackbarService,
    private zaakService: ZaakService,
  ) {
  }

  //
  // Getters / setters.
  //

  /**
   * Returns the field configurations for the form.
   */
  get form(): FieldConfiguration[] {
     return [
      ...this.caseDetailsFieldConfigurations,
      ...this.propertyFieldConfigurations,
      {
        label: 'Toelichting',
        placeholder: ' ',
        name: 'toelichting',
        required: false,
        value: this.zaak.toelichting,
      },
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
        value: this.zaak.identificatie,
        readonly: true,
      },
      {
        label: 'Vertrouwelijkheidaanduiding',
        name: 'vertrouwelijkheidaanduiding',
        value: this.zaak.vertrouwelijkheidaanduiding,
        choices: this.confidentialityChoices,
      },
      {
        activeWhen: (formGroup) => formGroup.getRawValue().vertrouwelijkheidaanduiding !== this.zaak.vertrouwelijkheidaanduiding,
        label: 'Reden wijziging vertrouwelijkheidniveau',
        name: 'reden',
        maxlength: 80,
        placeholder: 'Reden wijziging vertrouwelijkheidniveau',
        value: '',
        required: true,
        writeonly: true,
      },
      {
        label: 'Omschrijving',
        maxlength: 80,
        name: 'omschrijving',
        placeholder: 'Geen omschrijving',
        required: true,
        value: this.zaak.omschrijving,
      },
    ];
  }

  /**
   * Returns the field configurations for the (readonly) properties.
   */
  get propertyFieldConfigurations(): FieldConfiguration[] {
    return this.zaaktypeEigenschappen.map((zaaktypeEigenschap: ZaaktypeEigenschap): FieldConfiguration => {
      const property = this.properties.find((p: EigenschapWaarde) => p.eigenschap.naam === zaaktypeEigenschap.name)
      const value = (property?.waarde) ? String(property.waarde) : null;
      const type = (zaaktypeEigenschap.spec.format === 'date') ? 'date' : null;

      return {
        choices: zaaktypeEigenschap.spec.enum,
        label: zaaktypeEigenschap.name,
        maxlength: zaaktypeEigenschap.spec.maxLength,
        placeholder: '-',
        readonly: false,
        required: false,
        value: value,
        format: zaaktypeEigenschap.spec.format,
        type: (zaaktypeEigenschap.spec.enum) ? 'select' : type,
      };
    })
  }

  /**
   * @type {boolean} Whether this component is loading.
   * */
  get isLoading(): boolean {
    return this.isCaseAPILoading || Boolean(this.isPropertyAPILoading);
  }

  /**
   * Whether user can force edit a closed case.
   * @returns {boolean}
   */
  get canForceEdit(): boolean {
    return !this.zaak.resultaat || this.zaak.kanGeforceerdBijwerken;
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
    this.zaakService.listCaseProperties(this.zaak.bronorganisatie, this.zaak.identificatie).subscribe(
      (data) => {
        this.properties = data;
        this.isCaseAPILoading = false;

      }, this.reportError.bind(this))
  }

  /**
   * Fetches the confidentiality choices
   */
  fetchConfidentialityChoices() {
    this.isCaseAPILoading = true;

    this.metaService.listConfidentialityClassifications().subscribe(
      (data) => {
        this.confidentialityChoices = data;
        this.isCaseAPILoading = false;
      }, this.reportError.bind(this))
  }

  /**
   * Updates this.zaakData with latest values from API.
   */
  fetchZaak() {
    this.isCaseAPILoading = true;
    this.zaakService.retrieveCaseDetails(this.zaak.bronorganisatie, this.zaak.identificatie).subscribe(
      (zaak: Zaak) => {
        this.tezzaLink = this.zaakService.createTezzaUrl(zaak);
        this.zaak = zaak;
        this.isCaseAPILoading = false;

        this.fetchZaakTypeEigenschappen(zaak);
      }, this.reportError.bind(this)
    );
  }

  /**
   * Updates this.zaakData with latest values from API.
   */
  fetchZaakTypeEigenschappen(zaak: Zaak) {
    this.isCaseAPILoading = true;
    this.metaService.getZaaktypeEigenschappenByUrl(zaak.zaaktype.url).subscribe(
      (zaaktypeEigenschappen: ZaaktypeEigenschap[]) => {
        this.zaaktypeEigenschappen = zaaktypeEigenschappen;
        this.isCaseAPILoading = false;
      }, this.reportError.bind(this)
    )
  }

  /**
   * Find matching key pairs in object
   * @param data
   * @param keys
   */
  findMatchingKeyPairs(data, keys) {
    return Object.entries(data)
      .filter(([key]) => keys.indexOf(key) > -1)
      .reduce((acc, [key, value]) => ({...acc, [key]: value}), {});
  }

  /**
   * Find mismatching key pairs in object
   * @param data
   * @param keys
   */
  findMismatchingKeyPairs(data, keys) {
    return Object.entries(data)
      .filter(([key]) => keys.indexOf(key) === -1 && key !== 'reden')
      .reduce((acc, [key, value]) => ({...acc, [key]: value}), {});
  }

  //
  // Events.
  //

  /***
   * Submits the form.
   * @param {Object} data
   */
  submitForm(data) {
    const propertyKeys = this.properties.map((propertyValue: EigenschapWaarde) => propertyValue.eigenschap.naam);
    const zaakKeys = Object.keys(this.zaak);

    const existingPropertyData = this.findMatchingKeyPairs(data, propertyKeys);
    const otherPropertyData = this.findMismatchingKeyPairs(data, propertyKeys);
    const zaakData = this.findMatchingKeyPairs(otherPropertyData, zaakKeys);
    const newPropertyData = this.findMismatchingKeyPairs(otherPropertyData, zaakKeys)

    // Property reden needs to be handled seperately
    if (data.reden) {
      zaakData['reden'] = data.reden;
    }

    this.updateProperties(existingPropertyData);
    this.createProperties(newPropertyData);
    this.updateZaak(zaakData);
  }

  /**
   * Submits the properties.
   * @param {Object} data
   */
  createProperties(data: Object): void {
    this.isCreatePropertyAPILoading = Object.entries(data).reduce((acc, [key, value], index) => {
      const newProperty: NieuweEigenschap = {
        naam: key,
        waarde: value,
        zaakUrl: this.zaak.url
      }

      if (newProperty.waarde) {
        this.zaakService.createCaseProperty(newProperty).subscribe(
          () => {},
          this.reportError.bind(this),
          () => this.isCreatePropertyAPILoading--,
        );
      }

      return acc + 1;
    }, 0);
  }

  goToLink(url: string){
    window.open(url, "_blank");
  }

  /**
   * Submits the properties.
   * @param {Object} data
   */
  updateProperties(data: Object): void {
    this.isPropertyAPILoading = Object.entries(data).reduce((acc, [key, value], index) => {
      const property = this.properties.find((propertyValue: EigenschapWaarde) => propertyValue.eigenschap.naam === key)
      property.waarde = value;

      this.zaakService.updateCaseProperty(property).subscribe(
        () => {},
        this.reportError.bind(this),
        () => this.isPropertyAPILoading = 0,
      );

      return acc + 1;
    }, 0);
  }

  /**
   * Submits the zaak.
   * @param {Object} zaakData
   */
  updateZaak(zaakData: Object): void {
    this.isCaseAPILoading = true;

    this.zaakService.updateCaseDetails(this.zaak.bronorganisatie, this.zaak.identificatie, zaakData).subscribe(
      () => {
        this.getContextData();
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
    const message = error.error?.value
      ? error.error?.value[0]
      : error?.error?.detail || error?.error.reason || error?.error[0]?.reason || error?.error.nonFieldErrors?.join(', ') || this.errorMessage;
    this.snackbarService.openSnackBar(message, 'Sluiten', 'warn');
    this.isCaseAPILoading = false;
    this.isPropertyAPILoading = 0;
    this.isCreatePropertyAPILoading = 0;
    console.error(error);
  }
}
