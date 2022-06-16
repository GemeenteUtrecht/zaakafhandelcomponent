import {Injectable} from '@angular/core';
import {Observable} from 'rxjs';
import {ApplicationHttpClient} from '@gu/services';
import { Permission, UserSearch } from '@gu/models';

@Injectable({
  providedIn: 'root'
})
export class AccountsService {
  constructor(private http: ApplicationHttpClient) {
  }

  /**
   * Retrieve user accounts.
   * @param {string} searchInput
   * @returns {Observable<UserSearch>}
   */
  getAccounts(searchInput?: string): Observable<UserSearch> {
    const endpoint = encodeURI(`/api/accounts/users?search=${searchInput}`);
    return this.http.Get<UserSearch>(endpoint);
  }

  /**
   * Request the permissions from API.
   */
  getPermissions(): Observable<Permission[]> {
    const endpoint = encodeURI(`/api/accounts/permissions`);
    return this.http.Get<Permission[]>(endpoint);
  }

  /**
   * Patches an access request
   * @param requestId
   * @param formData
   * @returns {Observable<any>}
   */
  patchAccessRequest(requestId, formData): Observable<any> {
    const endpoint = encodeURI(`/api/accounts/access-requests/${requestId}`);
    return this.http.Patch<any>(endpoint, formData);
  }

  /**
   *
   * @param formData
   * @returns {Observable<any>}
   */
  postAccessForCase(formData) {
    const endpoint = encodeURI('/api/accounts/cases/access');
    return this.http.Post<any>(endpoint, formData)
  }
}