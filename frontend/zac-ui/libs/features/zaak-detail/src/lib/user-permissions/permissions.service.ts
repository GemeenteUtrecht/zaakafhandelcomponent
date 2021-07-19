import {Injectable} from '@angular/core';
import {ApplicationHttpClient} from '@gu/services';
import {Observable} from 'rxjs';
import {Permission} from "@gu/models";


@Injectable()
export class PermissionsService {
  constructor(private http: ApplicationHttpClient) {
  }

  /**
   * Delete an atomic permission for a particular user
   * @param {Permission} permission
   * @return {Observable}
   */
  deletePermission(permission: Permission): Observable<any> {
    const endpoint = encodeURI(`/api/accounts/cases/access/${permission.id}`);
    return this.http.Delete(endpoint);
  }
}
