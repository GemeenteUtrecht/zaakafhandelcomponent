import {HttpParams} from "@angular/common/http";
import {Injectable} from '@angular/core';
import {Observable} from 'rxjs';
import {Geometry, ObjectType, Zaak, ZaakObject, ZaakObjectRelation} from "@gu/models";
import {ApplicationHttpClient} from '@gu/services';

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

    if(geometry) {
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
   * @return {string}
   */
  stringifyZaakObject(zaakObject: ZaakObject): string {
    return Object.entries(zaakObject.record.data)
      .filter(([key, value]) => ['objectid', 'status'].indexOf(key.toLowerCase()) === -1)
      .map(([key, value]) => `${key[0].toUpperCase() + key.slice(1)}: ${value}`)
      .sort()
      .join(', ');
  }

  /**
   * Converts a human-readable query to a valid API data_attrs value.
   * @param {string} [property] Object type property.
   * @param {string} query e.q.: "Naam van object" or "adres:Utrechtsestraat, type:Laadpaal"
   * @return {string} Value suitable for data_attrs argument.
   * @private
   */
  _parseQuery(property: string, query: string): string {
    return query.split(',')
      .map((part) => part.match(':') ? part : `${property}:${part}`)
      .map((keyValue) => keyValue.replace(/:\s*/g, ':').trim())
      .map((keyValue) => keyValue.replace(':', '__icontains__'))
      .join(',');
  }
}
