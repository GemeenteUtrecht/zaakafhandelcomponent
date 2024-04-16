import {Injectable} from '@angular/core';
import { forkJoin, Observable, of } from 'rxjs';
import {
  AuthProfile,
  MetaDocType,
  MetaZaaktype,
  Permission,
  Role, UserAuthProfile,
  UserGroupDetail,
  UserSearch
} from '@gu/models';
import { ApplicationHttpClient } from '@gu/services';
import { UserGroupList } from '../../../zaak-detail/src/models/user-group-search';
import { catchError } from 'rxjs/operators';
import { UserAuthProfiles } from '../../../../shared/data-access/models/accounts/user-auth-profile';

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
   * Delete authorization profile.
   */
  deleteAuthProfile(uuid): Observable<AuthProfile> {
    const endpoint = encodeURI(`/api/accounts/auth-profiles/${uuid}`);
    return this.http.Delete<AuthProfile>(endpoint);
  }

  /**
   * Create authorization profile.
   */
  createAuthProfile(data): Observable<AuthProfile> {
    const endpoint = encodeURI(`/api/accounts/auth-profiles`);
    return this.http.Post<AuthProfile>(endpoint, data);
  }

  /**
   * Update authorization profile.
   */
  updateAuthProfile(data, uuid): Observable<AuthProfile> {
    const endpoint = encodeURI(`/api/accounts/auth-profiles/${uuid}`);
    return this.http.Put<AuthProfile>(endpoint, data);
  }

  /**
   * Request the user authorization profiles from API.
   */
  getUserAuthProfiles(uuid, page?, pageSize = 50): Observable<UserAuthProfiles> {
    const pageValue = page ? `&page=${page}` : '';
    const endpoint = encodeURI(`/api/accounts/user-auth-profiles?auth_profile=${uuid}&pageSize=${pageSize}${pageValue}&is_active=true`);
    return this.http.Get<UserAuthProfiles>(endpoint);
  }

  /**
   * Create user authorization profile.
   */
  createUserAuthProfile(users, authProfileUuid): Observable<any> {
    const endpoint = encodeURI(`/api/accounts/user-auth-profiles`);
    if (users.length > 0) {
      const observables = [];
      users.forEach(user => {
        const data = {
          user: user.username,
          authProfile: authProfileUuid
        }
        observables.push(this.http.Post<UserAuthProfiles>(endpoint, data));
      });
      return forkJoin(observables)
    } else {
      return of(true);
    }
  }

  /**
   * Delete the user authorization profile.
   */
  deleteUserAuthProfile(userAuthProfiles: UserAuthProfile[]): Observable<any> {
    if (userAuthProfiles.length > 0) {
      const observables = [];
      userAuthProfiles.forEach(userAuthProfile => {
        const endpoint = encodeURI(`/api/accounts/user-auth-profiles/${userAuthProfile.id}`);
        observables.push(this.http.Delete<any>(endpoint));
      });
      return forkJoin(observables)
    } else {
      return of(true);
    }
  }

  /**
   * POST role to API
   */
  createRole(data): Observable<Role> {
    const endpoint = encodeURI(`/api/accounts/roles`);
    return this.http.Post<Role>(endpoint, data);
  }

  /**
   * Updates role.
   * @param {Role} role
   * @param {Object} data
   * @return {Observable}
   */
  updateRole(role: Role, data): Observable<Role> {
    const endpoint = encodeURI(`/api/accounts/roles/${role.id}`);
    return this.http.Put<Role>(endpoint, data);
  }

  /**
   * Delets role.
   * @param {Role} role
   * @return {Observable}
   */
  deleteRole(role: Role): Observable<any> {
    const endpoint = encodeURI(`/api/accounts/roles/${role.id}`);
    return this.http.Delete(endpoint);
  }

  /**
   * Request the permissions from API.
   */
  getPermissions(): Observable<Permission[]> {
    const endpoint = encodeURI(`/api/accounts/permissions`);
    return this.http.Get<Permission[]>(endpoint);
  }

  /**
   * Request document types
   */
  getDocTypes(): Observable<MetaDocType> {
    const endpoint = encodeURI("/api/core/informatieobjecttypen");
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
   * @param {UserGroupDetail[]} userGroups
   * @returns {Observable<any>}
   */
  getUserGroupDetailsBatch(userGroups: UserGroupDetail[]): Observable<any>{
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
