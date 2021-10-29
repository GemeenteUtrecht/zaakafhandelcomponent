import {Injectable} from '@angular/core';
import {Observable} from 'rxjs';
import { AuthProfile, MetaConfidentiality, MetaDocType, MetaZaaktype, Permission, Role } from '@gu/models';
import {ApplicationHttpClient} from '@gu/services';
import {CachedObservableMethod} from '@gu/utils';

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
   *
   */
  getDocTypes(): Observable<MetaDocType> {
    const endpoint = encodeURI("/api/core/document-types");
    return this.http.Get<MetaDocType>(endpoint);
  }

}
