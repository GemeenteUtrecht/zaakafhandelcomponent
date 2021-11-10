import {ChangeDetectionStrategy, ChangeDetectorRef, Component, Inject, OnInit, Renderer2} from '@angular/core';
import {TableSort, Zaak} from '@gu/models';
import {PageEvent} from '@angular/material/paginator';
import {MapGeometry, MapMarker} from "../../../../shared/ui/components/src/lib/components/map/map";
import {ZaakService} from "@gu/services";
import {DOCUMENT} from "@angular/common";
import {Router} from "@angular/router";

@Component({
  selector: 'gu-features-search',
  templateUrl: './features-search.component.html',
  styleUrls: ['./features-search.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class FeaturesSearchComponent implements OnInit{
  mapGeometries: MapGeometry[] = [];
  mapMarkers: MapMarker[] = [];

  resultData: Zaak[] = [];
  resultLength: number;
  sortData: TableSort;
  pageData: PageEvent;

  constructor(
    private changeDetectorRef: ChangeDetectorRef,
    private zaakService: ZaakService,
    private router: Router,
    private renderer2: Renderer2,
    @Inject(DOCUMENT) private document: Document) {
  }

  ngOnInit(): void {

    /*
     * /ui/zoeken route is now used for Oauth authorisation en can by configured via app.config.json: "redirectUri": "your_redirect_uri",
     * 'contezza-zac-doclib' script must by appended to complete Oauth login
     */
    if (this.router.url.includes('session_state')) {
      const script = this.renderer2.createElement('script');
      script.src = '/ui/assets/contezza-zac-doclib.js';
      this.renderer2.appendChild(this.document.body, script);
    }
  }

  //
  // Context.
  //

  /**
   * Gets the map geometreis to show on the map.
   * @return {MapGeometry[]}
   */
  getZaakMapGeometries(): MapGeometry[] {
    return this.resultData.map((zaak) => this.zaakService.zaakToMapGeometry(zaak, {
      onClick: () => {
        this.zaakService.navigateToCase(zaak);
      },
    }));
  }

  //
  // Events.
  //

  /**
   * Gets called when a map geometry callback is triggered.
   * @param {MapGeometry} mapGeometry
   */
  onMapGeometry(mapGeometry: MapGeometry): void {
    this.mapGeometries = [...this.getZaakMapGeometries(), mapGeometry];
  }

  /**
   * Gets called when a map marker callback is triggered.
   * @param {MapMarker[]} mapMarkers
   */
  onMapMarkers(mapMarkers: MapMarker[]): void {
    this.mapMarkers = mapMarkers;
  }

  /**
   * Gets called when te rersult is loaded.
   * @param {Zaak[]} cases
   */
  onLoadResult(cases: Zaak[]): void {
    this.resultData = cases
    this.mapGeometries = [...this.getZaakMapGeometries()];
    this.changeDetectorRef.detectChanges()
  }

  /**
   * Gets called on result length.
   * @param data
   */
  onResultLength(data): void {
    this.resultLength = data;
  }
}
