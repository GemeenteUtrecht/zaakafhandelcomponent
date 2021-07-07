import {Injectable} from '@angular/core';
import {Observable} from 'rxjs';
import {ApplicationHttpClient} from '@gu/services';
import {Permission, UserPermission} from './user-permission';


@Injectable()
export class UserPermissionsService {
  constructor(private http: ApplicationHttpClient) {
  }

  /**
   * List all users and their atomic permissions for a particular zaak
   * @param {string} bronorganisatie
   * @param {string} identificatie
   * @return {Observable}
   */
  getUserPermissions(bronorganisatie: string, identificatie: string): Observable<UserPermission[]> {
    const endpoint = encodeURI(`/api/core/cases/${bronorganisatie}/${identificatie}/atomic-permissions`);
    return this.http.Get<UserPermission[]>(endpoint);
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
