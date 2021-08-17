import {Component, EventEmitter, Output} from '@angular/core';
import {Choice, FieldConfiguration, SnackbarService} from '@gu/components';
import {ZaakObjectService} from './zaak-object.service';
import {ZaakObject} from './zaak-object';
import {excludeTownShipByName, getTownshipByName} from './geojson/townships';
import {Feature, Geometry} from "./geojson/geojson";
import {excludeProvinceByName, getProvinceByName} from './geojson/provinces';


/** @type {string} The name of utrecht in the provinces object. */
const PROVINCE_UTRECHT_NAME = 'Utrecht';

/** @type {string} The name of utrecht in the townships object. */
const TOWNSHIP_UTRECHT_NAME = 'Utrecht (Ut)';


const OBJECT_SEARCH_GEOMETRY_CHOICES: Choice[] = [
  {
    label: `Gemeente ${TOWNSHIP_UTRECHT_NAME}`,
    value: JSON.stringify(getTownshipByName(TOWNSHIP_UTRECHT_NAME).geometry),
  },

  {
    label: `Provincie ${PROVINCE_UTRECHT_NAME}`,
    value: JSON.stringify(getProvinceByName(PROVINCE_UTRECHT_NAME).geometry),
  },

  // ...excludeTownShipByName(TOWNSHIP_UTRECHT_NAME)
  //   .map((feature: Feature) => ({
  //     label: `Gemeente ${feature.properties.name}`,
  //     value: JSON.stringify(feature.geometry)
  //   })),
  //
  ...excludeProvinceByName(PROVINCE_UTRECHT_NAME)
    .map((feature: Feature) => ({
      label: `Provincie ${feature.properties.name}`,
      value: JSON.stringify(feature.geometry)
    })),
];

/**
 * <gu-zaak-object-search-form></gu-zaak-object-search-form>
 *
 * Shows a search form for zaak (case) objects.
 *
 * Emits selectZaakObject: ZaakObject after selecting a result zaak object.
 */
@Component({
  selector: 'gu-zaak-object-search-form',
  templateUrl: './zaak-object-search-form.component.html',
})
export class ZaakObjectSearchFormComponent {
  @Output() selectZaakObject: EventEmitter<ZaakObject> = new EventEmitter<ZaakObject>();

  readonly errorMessage = 'Er is een fout opgetreden bij het zoeken naar objecten.'

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

  constructor(public zaakObjectService: ZaakObjectService, private snackbarService: SnackbarService) {
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

  submitForm(data) {
    const geometry: Geometry = JSON.parse(data.geometry);

    this.zaakObjectService.searchObjects(geometry, data.query).subscribe(
      (zaakObjects: ZaakObject[]) => this.zaakObjects = zaakObjects,
      this.reportError.bind(this),
    );
  }

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    this.snackbarService.openSnackBar(this.errorMessage, 'Sluiten', 'warn');
    console.error(error);
  }
}
