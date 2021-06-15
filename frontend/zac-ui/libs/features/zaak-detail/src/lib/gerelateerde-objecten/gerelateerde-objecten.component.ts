import {Component, Input, OnInit} from '@angular/core';
import {GerelateerdeObjectenService } from "./gerelateerde-objecten.service";

@Component({
  selector: 'gu-gerelateerde-objecten',
  templateUrl: './gerelateerde-objecten.component.html',
  styleUrls: ['./gerelateerde-objecten.component.scss']
})
export class GerelateerdeObjectenComponent implements OnInit {
  @Input() bronorganisatie: string;
  @Input() identificatie: string;

  /** @type {boolean} Whether this component is loading. */
  isLoading: boolean;

  /** @type {Object[]} The list of groups of objects (Related objects are grouped on objecttype) */
  relatedObjects: Array<Object>;

  constructor(private gerelateerdeObjectenService: GerelateerdeObjectenService) { }

  ngOnInit(): void {
    this.fetchRelatedObjects();
  }

  /**
   * Fetches the objects related to a zaak
   */
  fetchRelatedObjects() {
    this.isLoading = true;

    this.gerelateerdeObjectenService.getRelatedObjects(
      this.bronorganisatie,
      this.identificatie
    ).subscribe(
      (data) => {
        this.relatedObjects = data;
        this.isLoading = false;
      },
      (error) => {
        console.error(error);
        this.isLoading = false;
      }
    );
  }

}
