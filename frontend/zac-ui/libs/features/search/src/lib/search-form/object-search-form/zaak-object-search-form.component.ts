import {Component, EventEmitter, Output} from '@angular/core';
import {Choice, FieldConfiguration, SnackbarService} from '@gu/components';
import {SearchService} from '../../search.service';
import {
  Feature,
  Geometry,
  ZaakObject,
  UtrechtNeighbourhoods,
  getProvinceByName,
  getTownshipByName,
} from '@gu/models';
import {ZaakObjectService} from '@gu/services';


/** @type {string} The name of utrecht in the provinces object. */
const PROVINCE_UTRECHT_NAME = 'Utrecht';

/** @type {string} The name of utrecht in the townships object. */
const TOWNSHIP_UTRECHT_NAME = 'Utrecht (Ut)';


const OBJECT_SEARCH_GEOMETRY_CHOICES: Choice[] = [
  {
    label: `Gemeente: ${TOWNSHIP_UTRECHT_NAME}`,
    value: JSON.stringify(getTownshipByName(TOWNSHIP_UTRECHT_NAME).geometry),
  },

  {
    label: `Provincie: ${PROVINCE_UTRECHT_NAME}`,
    value: JSON.stringify(getProvinceByName(PROVINCE_UTRECHT_NAME).geometry),
  },

  ...UtrechtNeighbourhoods.features.map((feature: Feature) => ({
    label: `Wijk: ${feature.properties.name}`,
    value: JSON.stringify(feature.geometry)
  })),
];

/**
 * <gu-zaak-object-search-form></gu-zaak-object-search-form>
 *
 * Shows a search form for zaak (case) objects.
 *
 * Emits loadResult: Zaak[] after selecting a Zaakobject.
 */
@Component({
  selector: 'gu-zaak-object-search-form',
  templateUrl: './zaak-object-search-form.component.html',
})
export class ZaakObjectSearchFormComponent {
  @Output() searchObjects: EventEmitter<void> = new EventEmitter<void>();
  @Output() selectZaakObject: EventEmitter<ZaakObject> = new EventEmitter<ZaakObject>();

  readonly errorMessage = 'Er is een fout opgetreden bij het zoeken naar objecten.'

  /** @type {boolean} Whether to show the zaak objecten. */
  showZaakObjecten = false;

  /** @type {FieldConfiguration[] Form configuration. */
  form: FieldConfiguration[] = [
    {
      choices: OBJECT_SEARCH_GEOMETRY_CHOICES,
      label: 'Gebied',
      name: 'geometry',
      required: true,
      value: OBJECT_SEARCH_GEOMETRY_CHOICES[0].value,
    },
    {
      label: 'Zoekopdracht',
      name: 'query',
      placeholder: 'adres:Utrechtsestraat 41, type:Laadpaal',
      required: false,
      value: '',
    }
  ];

  /** @type {ZaakObject[]} The search results for objects. */
  zaakObjects: ZaakObject[] = [];

  /**
   * Constructor method.
   * @param {SearchService} searchService
   * @param {ZaakObjectService} zaakObjectService
   * @param {SnackbarService} snackbarService
   */
  constructor(private searchService: SearchService, private zaakObjectService: ZaakObjectService, private snackbarService: SnackbarService) {
  }

  //
  // Getters / setters.
  //

  //
  // Angular lifecycle.
  //

  //
  // Context.
  //

  //
  // Events.
  //

  /**
   * Gers called when form is submitted.
   * @param {Object} data
   */
  submitForm(data): void {
    this.searchObjects.emit();

    const geometry: Geometry = JSON.parse(data.geometry);

    this.zaakObjects = [];
    this.showZaakObjecten = true;

    this.zaakObjectService.searchObjects(geometry, data.query).subscribe(
      (zaakObjects: ZaakObject[]) => this.zaakObjects = zaakObjects,
      this.reportError.bind(this),
    );
  }

  /**
   * Gets called when a ZaakObject is selected.
   * @param {Event} event
   * @param {ZaakObject} zaakObject
   */
  _selectZaakObject(event: Event, zaakObject: ZaakObject): void {
    this.selectZaakObject.emit(zaakObject);
    this.showZaakObjecten = false;
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
