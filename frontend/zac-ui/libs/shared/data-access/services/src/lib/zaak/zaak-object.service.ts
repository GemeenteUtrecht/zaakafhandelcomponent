import {Injectable} from '@angular/core';
import {ApplicationHttpClient} from '@gu/services';
import {Observable, Subscriber} from 'rxjs';
import {Geometry, ObjectType, Zaak, ZaakObject, ZaakObjectRelation} from "@gu/models";

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
   * Search for objects in the Objects API
   * @param {Geometry} geometry
   * @param {string} [query]
   * @return {Observable}
   */
  searchObjects(geometry: Geometry, query: string = ''): Observable<ZaakObject[]> {
    const endpoint = encodeURI('/api/core/objects');
    const search = {
      geometry: {
        within: geometry
      },
    }

    if (query) {
      search['data_attrs'] = this._parseQuery(query);
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
   * @param {string} query e.q.: "Naam van object" or "adres:Utrechtsestraat, type:Laadpaal"
   * @return {string} Value suitable for data_attrs argument.
   * @private
   */
  _parseQuery(query: string): string {
    return query.split(',')
      .map((part) => part.match(':') ? part : `name:${part}`)
      .map((keyValue) => keyValue.replace(/:\s*/g, ':').trim())
      .map((keyValue) => keyValue.replace(':', '__exact__'))
      .join(',');
  }
}
