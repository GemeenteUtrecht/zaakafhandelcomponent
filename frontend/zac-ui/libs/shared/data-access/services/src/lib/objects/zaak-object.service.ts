import {HttpParams} from "@angular/common/http";
import {Injectable} from '@angular/core';
import {Observable, Subscriber} from 'rxjs';
import { Geometry, PaginatedZaakObjects, User, Zaak, ZaakObject, ZaakObjectRelation } from '@gu/models';
import {ApplicationHttpClient, KadasterService} from '@gu/services';
import {MapMarker} from "../../../../../ui/components/src/lib/components/map/map";
import {ClearCacheOnMethodCall} from "@gu/utils";

@Injectable({
  providedIn: 'root'
})
export class ZaakObjectService {
  constructor(private http: ApplicationHttpClient, private kadasterService: KadasterService) {
  }

  /**
   * Relate an object to a zaak
   * @param {Zaak} zaak
   * @param {ZaakObject} zaakObject
   * @param {string} objectTypeDescription
   * @return {Observable}
   */
  @ClearCacheOnMethodCall('ZaakService.listRelatedObjects')
  createZaakObjectRelation(zaak: Zaak, zaakObject: ZaakObject, objectTypeDescription: string): Observable<ZaakObjectRelation> {
    const endpoint = encodeURI('/api/core/zaakobjects');
    return this.http.Post<ZaakObjectRelation>(endpoint, {
      zaak: zaak.url,
      object: zaakObject.url,
      objectType: "overige",
      objectTypeOverige: objectTypeDescription,
    })
  }

  /**
   * Removes the relation of an object to a zaak.
   * @param {string} zaakObjectRelationUrl
   */
  @ClearCacheOnMethodCall('ZaakService.listRelatedObjects')
  deleteZaakObjectRelation(zaakObjectRelationUrl: string): Observable<void> {
    const endpoint = encodeURI(`/api/core/zaakobjects?url=${zaakObjectRelationUrl}`);
    return this.http.Delete<void>(endpoint);
  }

  /**
   * Search for objects in the Objects API
   * @param {Geometry} geometry
   * @param {string} objectTypeUrl
   * @param {string} [property] Object type property.
   * @param {string} [query]
   * @param {number} [page]
   * @return {Observable}
   */
  searchObjects(geometry: Geometry, objectTypeUrl: string, property: string = '', query: string = '', page: number): Observable<PaginatedZaakObjects> {
    const pageValue = `?page=${page}`;
    const endpoint = encodeURI(`/api/core/objects${pageValue}`);
    const search = {
      type: objectTypeUrl,
    }

    if (geometry) {
      search['geometry'] = {
        within: geometry
      }
    }

    if (query) {
      if (property) {
        search['data_attrs'] = this._parseQuery(property, query);
      } else {
        search['data_icontains'] = query;
      }
    }

    return this.http.Post<PaginatedZaakObjects>(endpoint, search);
  }

  /**
   * Creates a string representation for a zaak object.
   * @param {ZaakObject} zaakObject
   * @param {number} [maxEntries] If set, the maximum amount of key/value pairs displayed.
   * @return {string}
   */
  stringifyZaakObject(zaakObject: ZaakObject, maxEntries: number = null): string {
    return ZaakObjectService._stringifyZaakObject(zaakObject, maxEntries);
  }

  /**
   * Creates a string representation for a zaak object.
   * @param {ZaakObject} zaakObject
   * @param {number} [maxEntries] If set, the maximum amount of key/value pairs displayed.
   * @return {string}
   */
  static _stringifyZaakObject(zaakObject: ZaakObject, maxEntries: number = null): string {
    console.log(zaakObject.record.data);
    return Object.entries(zaakObject.record.data)
      .filter(([key,]) => ['objectid', 'status'].indexOf(key.toLowerCase()) === -1)  // Filter unwanted keys.
      .filter(([, value]) => !(value?.toString().match(/^http/)))  // Filter URLs.
      .map(([key, value]) => `${key[0].toUpperCase() + key.slice(1)}: ${value}`)  // Create key/value string.
      .sort()  // Sort items alphabetically (key).
      .filter((value, index) => maxEntries === null || index < maxEntries)  // Limit entries
      .join(', ');  // Join string.
  }

  /**
   * Converts a ZaakObject to a MapMarker, ready to draw on the map.
   * If a pand is referenced in zaakObject, it's details are fetched and inlcuded on the MapMarker.
   * This operation is therefore asynchronous.
   * @param zaakObject
   * @param options
   * @return {Observable}
   */
  zaakObjectToMapMarker(zaakObject: ZaakObject, options: Object = {}): Observable<MapMarker> {
    // Return observable, this operation is async.
    return new Observable((subscriber: Subscriber<MapMarker>) => {
      const zaakObjectGeometry = zaakObject.record.geometry as Geometry;
      const mapMarker = zaakObjectGeometry?.type === 'Point' ? {
        contentProperties: [ ['stringRepresentation', zaakObject.stringRepresentation], ['start-case', zaakObject.url], ...Object.entries(zaakObject.record.data)],
        coordinates: zaakObjectGeometry?.coordinates?.length > 1
          ? [zaakObjectGeometry.coordinates[1], zaakObjectGeometry.coordinates[0]]
          : [],
        iconUrl: 'assets/vendor/leaflet/marker-icon-red.png',
      } as MapMarker : null;

      // Couldn't create a mapmarker (lacking coordinates?)
      if (!mapMarker) {
        subscriber.next(null);
        subscriber.complete();
      }

      // Assign options to created marker.
      Object.assign(mapMarker, options);

      // TODO: Check if pand data is used?
/*      // Find pand if referenced.
      if (zaakObject.record.data['BAGNR_PAND']) {
        this.kadasterService.retrievePandByPandId(zaakObject.record.data['BAGNR_PAND']).subscribe(
          // Add resolved pand details to map MapMarker.
          (pand) => {
            Object.assign(
              mapMarker.contentProperties,
              Object
                .entries(pand)
                .filter(([key, value]) => Object(value) !== value)  // Only keep primitive values.
                .reduce((acc, [key, value]) => ({...acc, key: value}), {})  // Convert back to object.
            );

            // Complete with pand.
            subscriber.next(mapMarker);
            subscriber.complete();
          }
        );
      } else {
        // Complete without pand.
      }*/

      subscriber.next(mapMarker);
      subscriber.complete();
    });
  }

  /**
   * Converts a human-readable query to a valid API data_attrs value.
   * @param {string} [property] Object type property.
   * @param {string} query e.q.: "Naam van object" or "adres:Utrechtsestraat, type:Laadpaal"
   * @return {string} Value suitable for data_attrs argument.
   * @private
   */
  private _parseQuery(property: string, query: string): string {
    return query.split(',')
      .map((part) => part.match(':') ? part : `${property}:${part}`)
      .map((keyValue) => keyValue.replace(/:\s*/g, ':').trim())
      .map((keyValue) => keyValue.replace(':', '__icontains__'))
      .join(',');
  }


}
