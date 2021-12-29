import {HttpParams} from "@angular/common/http";
import {Injectable} from '@angular/core';
import {Observable} from 'rxjs';
import {Geometry, Zaak, ZaakObject, ZaakObjectRelation} from "@gu/models";
import {ApplicationHttpClient} from '@gu/services';
import {MapMarker} from "../../../../../ui/components/src/lib/components/map/map";
import {ClearCacheOnMethodCall} from "@gu/utils";

@Injectable({
  providedIn: 'root'
})
export class ZaakObjectService {
  constructor(private http: ApplicationHttpClient) {
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
    const endpoint = encodeURI('/api/core/zaakobjects');
    const params = new HttpParams().set('url', zaakObjectRelationUrl);
    return this.http.Delete<void>(endpoint, {params: params});
  }

  /**
   * Search for objects in the Objects API
   * @param {Geometry} geometry
   * @param {string} objectTypeUrl
   * @param {string} [property] Object type property.
   * @param {string} [query]
   * @return {Observable}
   */
  searchObjects(geometry: Geometry, objectTypeUrl: string, property: string = '', query: string = ''): Observable<ZaakObject[]> {
    const endpoint = encodeURI('/api/core/objects');
    const search = {
      type: objectTypeUrl,
    }

    if (geometry) {
      search['geometry'] = {
        within: geometry
      }
    }

    if (query) {
      search['data_attrs'] = this._parseQuery(property, query);
    }

    return this.http.Post<ZaakObject[]>(endpoint, search);
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
    return Object.entries(zaakObject.record.data)
      .filter(([key,]) => ['objectid', 'status'].indexOf(key.toLowerCase()) === -1)  // Filter unwanted keys.
      .filter(([, value]) => !value.match(/^http/))  // Filter URLs.
      .map(([key, value]) => `${key[0].toUpperCase() + key.slice(1)}: ${value}`)  // Create key/value string.
      .sort()  // Sort items alphabetically (key).
      .filter((value, index) => maxEntries === null || index < maxEntries)  // Limit entries
      .join(', ');  // Join string.
  }

  /**
   * Converts a ZaakObject to a MapMarker, ready to draw on the map.
   * @param zaakObject
   * @param options
   */
  zaakObjectToMapMarker(zaakObject: ZaakObject, options: Object = {}): MapMarker {
    const zaakObjectGeometry = zaakObject.record.geometry as Geometry;
    const mapMarker = zaakObjectGeometry?.type === 'Point' ? {

      title: ZaakObjectService._stringifyZaakObject(zaakObject),
      coordinates: zaakObjectGeometry?.coordinates?.length > 1
        ? [zaakObjectGeometry.coordinates[1], zaakObjectGeometry.coordinates[0]]
        : [],
      iconUrl: 'assets/images/map/marker-icon-red.png',

    } as MapMarker : null;

    if (mapMarker) {
      Object.assign(mapMarker, options);
    }
    return mapMarker;
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
