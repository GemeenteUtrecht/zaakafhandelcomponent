import {Component, Input, OnInit} from '@angular/core';
import {FieldConfiguration, ModalService, SnackbarService} from '@gu/components';
import { ObjectType, RowData, Table, Zaak, ZaakObject, ZaakObjectGroup } from '@gu/models';
import { ObjectsService, ZaakObjectService, ZaakService } from '@gu/services';

/**
 * <gu-gerelateerde-objecten [bronorganisatie]="bronorganisatie" [identificatie]="identificatie"></gu-gerelateerde-objecten>
 *
 * Shows related objects for a case (zaak).
 *
 * Requires bronorganisatie: string input to identify the organisation.
 * Requires identificatie: string input to identify the case (zaak).
 */
@Component({
  selector: 'gu-gerelateerde-objecten',
  templateUrl: './gerelateerde-objecten.component.html',
  styleUrls: ['./gerelateerde-objecten.component.scss']
})
export class GerelateerdeObjectenComponent implements OnInit {
  @Input() zaak: Zaak;

  /** @type {string} Possible error message. */
  readonly errorMessage = 'Er is een fout opgetreden bij het zoeken naar gerelateerde objecten.'

  /** @type {string} Modal id. */
  readonly modalObjectSearchId = 'related-objects-object-search-modal';

  /** @type {string} Modal id. */
  readonly modalFormId = 'related-objects-form-modal';

  /** @type {ZaakObject} The selected zaak object (to relate to resolved zaak). */
  activeZaakObject: ZaakObject = null;

  /** @type {boolean} Whether this component is loading. */
  isLoading: boolean;

  /** @type {boolean} Whether this component is loading. */
  isInitiating: boolean;

  /** @type {ZaakObjectGroup[]} The list of groups of objects (Related objects are grouped on objecttype) */
  relatedObjects: ZaakObjectGroup[];

  /** @type {{ title: string, table: Table }[]} The tables to render. */
  tables: { title: string, table: Table }[] = [];

  /** @type {FieldConfiguration[]} The (modal) form. */
  form: FieldConfiguration[] = null;

  /**
   * Constructor method.
   * @param {ModalService} modalService
   * @param {ObjectsService} objectsService
   * @param {SnackbarService} snackbarService
   * @param {ZaakService} zaakService
   * @param {ZaakObjectService} zaakObjectService
   */
  constructor(
    private modalService: ModalService,
    private objectsService: ObjectsService,
    private snackbarService: SnackbarService,
    private zaakService: ZaakService,
    private zaakObjectService: ZaakObjectService) {
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
  }

  /**
   * A function optionally passed into the NgForOf directive to customize how NgForOf uniquely identifies items in an
   * iterable.
   *
   * In all of these scenarios it is usually desirable to only update the DOM elements associated with the items
   * affected by the change. This behavior is important to:
   *
   *  - preserve any DOM-specific UI state (like cursor position, focus, text selection) when the iterable is modified
   *  - enable animation of item addition, removal, and iterable reordering
   *  - preserve the value of the <select> element when nested <option> elements are dynamically populated using NgForOf
   *    and the bound iterable is updated
   *
   * @param {number} index
   * @param {Table} table
   * @return {number}
   */
  trackRow(index: number, table: Table) {
    return this.tables?.findIndex((titleAndTable: { title: string, table: Table }) => titleAndTable.table === table);
  }

  //
  // Context.
  //

  /**
   * Fetches the objects related to a zaak
   */
  getContextData(): void {
    this.isInitiating = true;
    this.tables = [];

    this.zaakService.listRelatedObjects(this.zaak.bronorganisatie, this.zaak.identificatie).subscribe(
      (data) => {
        this.relatedObjects = data;
        this.getTables();
      },
      this.reportError.bind(this)
    );
  }

  /**
   * Returns the tables to render.
   * @returns {{title: string, table: Table}[]}
   */
   getTables() {
     this.relatedObjects.map((group: ZaakObjectGroup) => {
      /* Use the latest version of the ObjectType to make the table headers */
      const latestZaakObjectGroup = group.items[0];
      const latestZaakObjectGroupType = latestZaakObjectGroup.type as ObjectType;

      let tableGroup;
      return this.objectsService.readLatestObjectTypeVersion(latestZaakObjectGroupType).subscribe(objectTypeVersion => {
        const objectProperties = objectTypeVersion.jsonSchema.required;

        const tableHead: string[] = [
          ...objectProperties.filter((property): boolean => property !== 'objectid'),
          'acties',
        ]

        const tableBody: RowData[] = group.items.map((relatedObject: ZaakObject) => {
          const cellData = tableHead.reduce((acc, val: string) => {
            acc[val] = String(relatedObject.record.data[val] || '');
            return acc;
          }, {});

          // Hide button if case is closed and the user is not allowed to force edit
          cellData['acties'] = !this.zaak.resultaat || this.zaak.kanGeforceerdBijwerken ? {
            label: 'Verwijderen',
            name: 'delete',
            type: 'button',
            value: relatedObject,
          } : ''

          const nestedCellData = Object.entries(relatedObject.record)
            .filter(([, value]) => value !== null)
            .filter(([, value]) => !Array.isArray(value))
            .filter(([, value]) => typeof value !== 'object')
            .reduce((acc: {}, [key, value]) => {

              // typeVersion -> type version.
              const _key = key[0] + key.slice(1).replace(
                /[A-Z]/,
                (str: string) => ` ${str.toLowerCase()}`
              )

              // Date
              if (key.match(/at$/i)) {
                const _value = {
                  type: 'date',
                  date: value
                }
                acc[_key] = _value
                return acc;
              }

              acc[_key] = value;
              return acc;
            }, {})

          return {
            cellData: cellData,
            nestedTableData: new Table((Object.keys(nestedCellData)), [{
              cellData: nestedCellData,
            }]),
          };
        });

        const table = new Table(tableHead, tableBody);
        tableGroup = {title: group.label, table: table};

        this.tables.push(tableGroup)
      })
    });
  }

  /**
   * Returns the (modal) form.
   * @return {FieldConfiguration[]}
   */
  getForm(): FieldConfiguration[] {
    return [
      {
        label: 'Gerelateerd object toevoegen:',
        name: 'object',
        readonly: true,
        value: (this.activeZaakObject)
          ? this.zaakObjectService.stringifyZaakObject(this.activeZaakObject)
          : null,
      },
      {
        label: 'Beschrijving',
        name: 'objectTypeDescription',
        pattern: "[a-zA-Z0-9]+[a-zA-Z0-9 ]+",
        placeholder: 'Beschrijving van het type object (maximaal 100 tekens).',
        value: '',
      }
    ];
  }

  //
  // Events.
  //

  /**
   * Gets called when the add related object button is clicked.
   * @param {Event} event
   */
  addClick(event: Event): void {
    this.modalService.open(this.modalObjectSearchId);
  }

  /**
   * Gets called when the form is submitted.
   * @param {Object} data
   */
  formSubmit(data): void {
    this.isLoading = true;
    this.zaakService.retrieveCaseDetails(this.zaak.bronorganisatie, this.zaak.identificatie).subscribe(
      (zaak) => this.zaakObjectService
        .createZaakObjectRelation(zaak, this.activeZaakObject, String(data.objectTypeDescription).toLowerCase())
        .subscribe(
          () => {
            this.modalService.close(this.modalFormId);
            this.getContextData();
          },
          this.reportError.bind(this),
          () => this.isLoading = false,
        ),
      this.reportError.bind(this),
    );
  }

  /**
   * Gets called when a zaak object is selected.
   * @param {ZaakObject} zaakObject
   */
  selectZaakObject(zaakObject: ZaakObject): void {
    this.activeZaakObject = zaakObject;
    this.form = this.getForm();
    this.modalService.close(this.modalObjectSearchId);
    this.modalService.open(this.modalFormId);
  }

  /**
   * Gets called when a delete button in the table is pressed.
   * @param {Object} data
   */
  tableButtonClick(data: { 'acties': ZaakObject }): void {
    this.isLoading = true;

    this.zaakObjectService.deleteZaakObjectRelation(data.acties.zaakobjectUrl).subscribe(
      this.getContextData.bind(this),
      this.reportError.bind(this),
      () => this.isLoading = false
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
    const message = error?.error?.detail || error?.error[0]?.reason || error?.error.nonFieldErrors?.join(', ') || this.errorMessage;
    this.snackbarService.openSnackBar(message, 'Sluiten', 'warn');
    console.error(error);
    this.isLoading = false;
  }

}
