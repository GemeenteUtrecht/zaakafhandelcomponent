import {Component, Input, OnInit} from '@angular/core';
import {Table} from "@gu/models";
import {GroupGerelateerdeObjecten, GerelateerdeObject} from '../../models/group-gerelateerde-objecten';
import {ZaakService} from "@gu/services";

@Component({
  selector: 'gu-gerelateerde-objecten',
  templateUrl: './gerelateerde-objecten.component.html',
  styleUrls: ['./gerelateerde-objecten.component.scss']
})
export class GerelateerdeObjectenComponent implements OnInit {
  @Input() bronorganisatie: string;
  @Input() identificatie: string;

  /* Whether this component is loading. */
  isLoading: boolean;

  /* The list of groups of objects (Related objects are grouped on objecttype) */
  relatedObjects: Array<GroupGerelateerdeObjecten>;

  /* Each item in the array contains the label of the objecttype and a table with the objects of that type */
  tablesData: Array<object>;

  constructor(
    private zaakService: ZaakService,
  ) {
  }

  ngOnInit(): void {
    this.fetchRelatedObjects();
  }

  /**
   * Fetches the objects related to a zaak
   */
  fetchRelatedObjects() {
    this.isLoading = true;

    this.zaakService.listRelatedObjects(
      this.bronorganisatie,
      this.identificatie
    ).subscribe(
      (data) => {
        this.relatedObjects = data;

        this.tablesData = data.map((group: GroupGerelateerdeObjecten) => {
          return this.formatGroupData(group)
        })

        this.isLoading = false;
      },
      (error) => {
        console.error(error);
        this.isLoading = false;
      }
    );
  }

  formatGroupData(group: GroupGerelateerdeObjecten): object {
    /* Use the latest version of the ObjectType to make the table headers */
    const objectProperties: [] = group.items[0]
      .type.versions[group.items[0].type.versions.length - 1]
      .jsonSchema.required;

    let tableHeader: string[] = objectProperties.filter((property, index): boolean => {
      return property !== 'objectid';
    });

    /* Iterate over the items to populate the table */
    let tableContent: Array<any> = group.items.map((relatedObject: GerelateerdeObject) => {
      /* Filter object data so that only required properties are shown */
      const objectData = {};
      tableHeader.forEach((propertyName: string): void => {
        const propertyValue: any = relatedObject.record.data[propertyName];
        objectData[propertyName] = propertyValue ? String(propertyValue) : '';
      });

      return {
        cellData: objectData
      };
    });

    const table = new Table(tableHeader, tableContent);
    return {title: group.label, table: table};
  }

}
