import {Injectable} from '@angular/core';
import { forkJoin, Observable, of } from 'rxjs';
import {
  AuthProfile,
  MetaDocType,
  MetaZaaktype,
  Permission,
  Role, UserGroupDetail
} from '@gu/models';
import {ApplicationHttpClient} from '@gu/services';
import { UserGroupList, UserGroupResult } from '../../../zaak-detail/src/models/user-group-search';
import { catchError } from 'rxjs/operators';
import { UserSearch } from '../../../zaak-detail/src/models/user-search';

@Injectable({
  providedIn: 'root'
})
export class FeaturesAuthProfilesService {

  constructor(private http: ApplicationHttpClient) {
  }

  /**
   * Request the authorization profiles from API.
   */
  getAuthProfiles(): Observable<AuthProfile[]> {
    const endpoint = encodeURI(`/api/accounts/auth-profiles`);
    return this.http.Get<AuthProfile[]>(endpoint);
  }

  /**
   * Request the authorization profiles from API.
   */
  createAuthProfile(data): Observable<AuthProfile> {
    const endpoint = encodeURI(`/api/accounts/auth-profiles`);
    return this.http.Post<AuthProfile>(endpoint, data);
  }

  /**
   * Request the roles from API.
   */
  getRoles(): Observable<Role[]> {
    const endpoint = encodeURI(`/api/accounts/roles`);
    return this.http.Get<Role[]>(endpoint);
  }

  /**
   * POST role to API
   */
  createRole(data): Observable<Role> {
    const endpoint = encodeURI(`/api/accounts/roles`);
    return this.http.Post<Role>(endpoint, data);
  }

  /**
   * Request the permissions from API.
   */
  getPermissions(): Observable<Permission[]> {
    const endpoint = encodeURI(`/api/accounts/permissions`);
    return this.http.Get<Permission[]>(endpoint);
  }

  /**
   * Request the authorization profiles from API.
   */
  getCaseTypes(): Observable<MetaZaaktype> {
    const endpoint = encodeURI(`/api/core/zaaktypen`);
    return this.http.Get<MetaZaaktype>(endpoint);
  }

  /**
   * Request document types
   */
  getDocTypes(): Observable<MetaDocType> {
    const endpoint = encodeURI("/api/core/document-types");
    return this.http.Get<MetaDocType>(endpoint);
  }

  /**
   * List User groups
   */
  listUserGroups(): Observable<UserGroupList> {
    const endpoint = encodeURI("/api/accounts/groups")
    return this.http.Get<UserGroupList>(endpoint);
  }

  /**
   * Get details per user group
   * @param {UserGroupResult[]} userGroups
   * @returns {Observable<any>}
   */
  getUserGroupDetailsBatch(userGroups: UserGroupResult[]): Observable<any>{
    const observables = [];
    userGroups.forEach(group => {
      if (group.id) {
        const endpoint = encodeURI(`/api/accounts/groups/${group.id}`);
        observables.push(this.http.Get<any>(endpoint).pipe(catchError(() => of(null))));
      } else {
        observables.push(of(null));
      }
    });
    return forkJoin(observables)
  }

  /**
   * POST user group to API
   */
  createUserGroup(data): Observable<UserGroupDetail> {
    const endpoint = encodeURI(`/api/accounts/groups`);
    return this.http.Post<UserGroupDetail>(endpoint, data);
  }


  /**
   * PUT user group to API
   */
  updateUserGroup(data, id): Observable<UserGroupDetail> {
    const endpoint = encodeURI(`/api/accounts/groups/${id}`);
    return this.http.Put<UserGroupDetail>(endpoint, data);
  }

  /**
   * Delete user group
   */
  deleteUserGroup(id): Observable<UserGroupDetail> {
    const endpoint = encodeURI(`/api/accounts/groups/${id}`);
    return this.http.Delete<UserGroupDetail>(endpoint);
  }

  /**
   * Retrieve user accounts
   * @param {string} searchInput
   * @returns {Observable<UserSearch>}
   */
  getAccounts(searchInput: string): Observable<UserSearch> {
    const endpoint = encodeURI(`/api/accounts/users?search=${searchInput}`);
    return this.http.Get<UserSearch>(endpoint);
  }

}
