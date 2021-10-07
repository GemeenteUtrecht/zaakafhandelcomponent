import {Injectable} from '@angular/core';
import {Observable} from 'rxjs';
import {ApplicationHttpClient} from '@gu/services';
import {ObjectType, ObjectTypeVersion} from '@gu/models';

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
