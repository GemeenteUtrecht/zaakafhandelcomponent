import {Injectable} from '@angular/core';
import {ApplicationHttpClient} from '@gu/services';
import {Observable} from 'rxjs';
import {ZaakPermission} from "@gu/models";


@Injectable()
export class PermissionsService {
  constructor(private http: ApplicationHttpClient) {
  }

  /**
   * Delete an atomic permission for a particular user
   * @param {ZaakPermission} permission
   * @return {Observable}
   */
  deletePermission(permission: ZaakPermission): Observable<any> {
    const endpoint = encodeURI(`/api/accounts/cases/access/${permission.id}`);
    return this.http.Delete(endpoint);
  }
}
