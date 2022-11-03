import {ChangeDetectorRef, Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {Choice, FieldConfiguration, SnackbarService} from '@gu/components';
import {
  Feature,
  Geometry,
  getProvinceByName,
  getTownshipByName,
  ObjectType,
  ObjectTypeVersion, Position,
  UtrechtNeighbourhoods,
  ZaakObject, Zaaktype,
} from '@gu/models';
import {ObjectsService, ZaakObjectService} from '@gu/services';
import {SearchService} from '../../search.service';
import {MapGeometry, MapMarker} from "../../../../../../shared/ui/components/src/lib/components/map/map";


/** @type {string} The name of utrecht in the provinces object. */
const PROVINCE_UTRECHT_NAME = 'Utrecht';

/** @type {string} The name of utrecht in the townships object. */
const TOWNSHIP_UTRECHT_NAME = 'Utrecht (Ut)';


/** @type {Choice[]} The choices for the geometry <select>. */
const OBJECT_SEARCH_GEOMETRY_CHOICES: Choice[] = [
  {
    label: '',
    value: 'null',
  },
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
  styleUrls: ['./zaak-object-search-form.component.scss'],
  templateUrl: './zaak-object-search-form.component.html',
})
export class ZaakObjectSearchFormComponent implements OnInit {
  @Input() zaaktype: Zaaktype = null;
  @Output() searchObjects: EventEmitter<void> = new EventEmitter<void>();
  @Output() selectZaakObject: EventEmitter<ZaakObject> = new EventEmitter<ZaakObject>();
  @Output() mapGeometry: EventEmitter<MapGeometry> = new EventEmitter<MapGeometry>();
  @Output() mapMarkers: EventEmitter<any> = new EventEmitter<{ coordinates: Position[] }>();
  @Output() isLoadingResult: EventEmitter<boolean> = new EventEmitter<boolean>();

  readonly errorMessage = 'Er is een fout opgetreden bij het zoeken naar objecten.';

  /** @type {boolean}} Whether the component is loading. */
  isLoading = true;

  /** @type {boolean} Whether to show the zaak objecten. */
  showZaakObjecten = false;

  /** @type {boolean} Whether to include all object types. */
  includeAllObjectTypes = false;

  /** @tupe {ObjectType[]} The object types. */
  objectTypes: ObjectType[] = [];

  /** @type {ObjectTypeVersion} The latest object type version for every object type in this.objectTypes. */
  objectTypeVersions: ObjectTypeVersion[] = []

  /** @type {ZaakObject[]} The search results for objects. */
  zaakObjects: ZaakObject[] = [];

  /**
   * Constructor method.
   * @param {ObjectsService} objectsService
   * @param {SearchService} searchService
   * @param {ZaakObjectService} zaakObjectService
   * @param {SnackbarService} snackbarService
   * @param {ChangeDetectorRef} cdRef
   */
  constructor(
    private objectsService: ObjectsService,
    private searchService: SearchService,
    private zaakObjectService: ZaakObjectService,
    private snackbarService: SnackbarService,
    private cdRef: ChangeDetectorRef,
  ) {
  }

  //
  // Getters / setters.
  //

  /**
   *  @type {FieldConfiguration[] Form configuration.
   */
  get form(): FieldConfiguration[] {
    return [
      this.objectTypesAsFieldConfiguration(),
      {
        activeWhen: (formGroup) => {
          const objectTypeURL = formGroup.getRawValue().objectType;
          const objectType = this.objectTypes.find((o: ObjectType) => o.url === objectTypeURL);
          return objectType?.allowGeometry
        },
        choices: OBJECT_SEARCH_GEOMETRY_CHOICES,
        label: 'Gebied',
        name: 'geometry',
        required: false,
        value: OBJECT_SEARCH_GEOMETRY_CHOICES[0].value,
      },
      ...this.objectTypeVersionsAsFieldConfigurations(),
      {
        label: 'Zoekopdracht',
        name: 'query',
        placeholder: 'adres:Utrechtsestraat 41, type:Laadpaal',
        required: false,
        value: '',
      },
      {
        activeWhen: () => this.zaaktype,
        checked: this.includeAllObjectTypes,
        label: 'Toon objecttypen van alle zaaktypen.',
        name: 'include_all_object_types',
        type: 'checkbox',
        onChange: (e, field) => {
          this.includeAllObjectTypes = !field.checked;
          this.getContextData();
        },
      },
    ];
  }

  //
  // Angular lifecycle.
  //

  /**
   * A lifecycle hook that is called after Angular has initialized all data-bound properties of a directive. Define an
   * ngOnInit() method to handle any additional initialization tasks.
   */
  ngOnInit(): void {
    this.getContextData();
    this.fetchObjects()
  }

  //
  // Context.
  //

  getContextData(): void {
    this.isLoading = true;
    this.isLoadingResult.emit(true);

    const observable = (this.includeAllObjectTypes || !this.zaaktype)
      ? this.objectsService.listObjectTypes()
      : this.objectsService.listObjectTypesForZaakType(this.zaaktype)

    observable.subscribe(
      this.getObjectTypesContext.bind(this),
      (error) => {
        this.reportError(error)
        this.isLoading = false;
        this.isLoadingResult.emit(false);
      }
    )
  }

  /**
   * Sets/fetches this.objectTypes and this.objectTypeVersions.
   * @param {ObjectType[]} objectTypes.
   */
  getObjectTypesContext(objectTypes: ObjectType[]): void {
    this.objectTypes = [];
    this.objectTypeVersions = [];
    const objectTypeVersions = [];
    let loadingLength = objectTypes.length;

    if (!loadingLength) {
      this.isLoading = false;
      this.isLoadingResult.emit(false);
    }

    objectTypes.forEach((objectType: ObjectType) => {
        this.isLoading = true;
        this.isLoadingResult.emit(true);

        this.objectsService
          .readLatestObjectTypeVersion(objectType)
          .subscribe(
            (objectTypeVersion) => objectTypeVersions.push(objectTypeVersion),
            (...args) => this.reportError(...args),
            () => {
              loadingLength -= 1;

              if (loadingLength === 0) {
                this.objectTypes = objectTypes;
                this.objectTypeVersions = objectTypeVersions;
                this.cdRef.detectChanges();
              }

              this.isLoading = false;
              this.isLoadingResult.emit(false);
            }
          );
      }
    );
  }

  /**
   * Returns a select (configuration) for object types.
   * @return {FieldConfiguration}
   */
  objectTypesAsFieldConfiguration(): FieldConfiguration {
    const choices: Choice[] = [
      {
        label: '',
        value: '',
      },
      ...this.objectTypes.map((objectType: ObjectType) => ({
        label: objectType.name,
        value: objectType.url
      }))
    ];

    return {
      choices: choices,
      label: 'Object type',
      name: 'objectType',
      required: false,
      value: choices[0].value,
    }
  }

  /**
   * Returns a FieldConfiguration[] for object type versions.
   * @return {FieldConfiguration[]}
   */
  objectTypeVersionsAsFieldConfigurations(): FieldConfiguration[] {
    return this.objectTypeVersions.map((objectTypeVersion: ObjectTypeVersion) => {
      const objectType = this.objectTypes.find((o) => o.url === objectTypeVersion.objectType);
      const properties = objectTypeVersion.jsonSchema.properties;

      if (!properties) {
        return;
      }

      const choices = Object
        .keys(properties)
        .map((propertyName): Choice => ({
          label: propertyName,
          value: propertyName,
        }));

      return {
        activeWhen: (formGroup) => formGroup.getRawValue().objectType?.indexOf(objectType.uuid) > -1,  // Only active when the matching object type is selected.
        choices: choices,
        label: 'Eigenschap',
        name: `property`,
        key: `${objectType.uuid}.property`,
        required: false,
        value: choices[0].value,
      }
    }).filter(f => f);
  }

  /**
   * Search for objects in the Objects API
   * @param {Geometry} geometry
   * @param {string} objectType
   * @param {string} [property] Object type property.
   * @param {string} [query]
   */
  fetchObjects(geometry = null, objectType = null, property = null, query = null): void {
    this.zaakObjectService.searchObjects(geometry, objectType, property, query).subscribe(
      (zaakObjects: ZaakObject[]) => {
        this.zaakObjects = zaakObjects;

        let activeMapMarkers = []

        if (!zaakObjects.length) {
          this.isLoading = false;
          this.isLoadingResult.emit(false);
          return;
        }

        // Fetch zaak objects.
        this.zaakObjects.forEach((zaakObject: ZaakObject) => {
          const mapMarkerOptions = {
            onClick: (event) => this._selectZaakObject(event, zaakObject),
          }

          // Async zaakObjectToMapMarker
          this.zaakObjectService.zaakObjectToMapMarker(zaakObject, mapMarkerOptions).subscribe(
            // Add map marker.
            (mapMarker: MapMarker) => {
              if (mapMarker) {
                activeMapMarkers = [...activeMapMarkers, mapMarker];
              }
            },

            // Report error.
            this.reportError.bind(this),

            // All map markers loaded.
            () => {
              this.mapMarkers.emit(activeMapMarkers);
              this.isLoading = false;
              this.isLoadingResult.emit(false);
              this.cdRef.detectChanges();
            })
        });
      },
      this.reportError.bind(this),
    );
  }

  //
  // Events.
  //

  /**
   * Gets called when form is changed.
   * @param {Object} data
   */
  changeForm(data) {
    const geometry = JSON.parse(data.geometry);
    this.mapGeometry.emit({geometry, editable: false})
  }

  /**
   * Gets called when form is submitted.
   * @param {Object} data
   */
  submitForm(data): void {
    this.searchObjects.emit();
    this.isLoading = true;
    this.isLoadingResult.emit(true);
    const geometry: Geometry = (data.geometry) ? JSON.parse(data.geometry) : null;

    this.zaakObjects = [];
    this.showZaakObjecten = true;

    this.fetchObjects(geometry, data.objectType, data.property, data.query)
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
    this.isLoading = false;
    this.isLoadingResult.emit(false);
    this.snackbarService.openSnackBar(this.errorMessage, 'Sluiten', 'warn');
    console.error(error);
  }
}
