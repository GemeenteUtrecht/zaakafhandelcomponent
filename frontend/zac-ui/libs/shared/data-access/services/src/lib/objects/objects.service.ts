import {Injectable} from '@angular/core';
import {Observable} from 'rxjs';
import {ApplicationHttpClient} from '@gu/services';
import {ObjectType, ObjectTypeVersion, Zaaktype} from '@gu/models';
import {HttpParams} from '@angular/common/http';

@Injectable({
  providedIn: 'root'
})
export class ObjectsService {

  /**
   * Constructor method.
   * @param {ApplicationHttpClient} http
   */
  constructor(
    private http: ApplicationHttpClient,
  ) {
  }

  /**
   * Retrieves all object types from the configured Objecttypes API.
   * @return {Observable}
   */
  listObjectTypes(): Observable<ObjectType[]> {
    const endpoint = encodeURI(`/api/core/objecttypes`);
    return this.http.Get<ObjectType[]>(endpoint);
  }

  /**
   * Retrieves all object types from the configured Objecttypes API.
   * @param {Zaaktype} zaaktype
   * @return {Observable}
   */
  listObjectTypesForZaakType(zaaktype: Zaaktype): Observable<ObjectType[]> {
    const endpoint = encodeURI(`/api/core/objecttypes`);
    const params = new HttpParams().set('zaaktype', zaaktype.url)
    return this.http.Get<ObjectType[]>(endpoint, {params: params});
  }

  /**
   * Reads the details of the latest objecttype version.
   * @param {ObjectType} objectType
   */
  readLatestObjectTypeVersion(objectType: ObjectType): Observable<ObjectTypeVersion> {
    return this.readObjectTypeVersion(objectType.uuid, String(objectType.versions.length))
  }

  /**
   * Read the details of a particular objecttype version.
   * @param {string} uuid
   * @param {string} version
   * @return {Observable}
   */
  readObjectTypeVersion(uuid: string, version: string) {
    const endpoint = encodeURI(`/api/core/objecttypes/${uuid}/versions/${version}`);
    return this.http.Get<any>(endpoint);
  }
}
