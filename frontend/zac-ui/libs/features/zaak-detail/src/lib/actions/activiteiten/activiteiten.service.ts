import { Injectable } from '@angular/core';
import { ApplicationHttpClient } from '@gu/services';
import { forkJoin, Observable, of } from 'rxjs';
import { Activity, ReadWriteDocument, UserSearch } from "@gu/models";
import { UserGroupList } from '../../../models/user-group-search';

@Injectable({
  providedIn: 'root'
})
export class ActiviteitenService {

  constructor(private http: ApplicationHttpClient) { }

  /**
   * Retrieve user accounts.
   * @param {string} searchInput
   * @returns {Observable<UserSearch>}
   */
  getAccounts(searchInput: string): Observable<UserSearch> {
    const endpoint = encodeURI(`/api/accounts/users?search=${searchInput}`);
    return this.http.Get<UserSearch>(endpoint);
  }

  /**
   * Retrieve user group list.
   * @param {string} searchInput
   * @returns {Observable<UserGroupList>}
   */
  getUserGroups(searchInput: string): Observable<UserGroupList>{
    const endpoint = encodeURI(`/api/accounts/groups?search=${searchInput}`);
    return this.http.Get<UserGroupList>(endpoint);
  }

  /**
   * Get documents for an activity.
   * @param {Activity[]} activities
   * @returns {Observable<any>}
   */
  getDocuments(activities: Activity[]): Observable<any> {
    const observables = [];
    activities.forEach(activity => {
      if (activity.document) {
        const endpoint = encodeURI(`/core/api/documents/info?document=${activity.document}`);
        observables.push(this.http.Get<any>(endpoint));
      } else {
        observables.push(of(null));
      }
    });
    return forkJoin(observables)
  }

  /**
   * Retrieve activities.
   * @param mainZaakUrl
   * @returns {Observable<Activity[]>}
   */
  getActivities(mainZaakUrl): Observable<Activity[]> {
    const endpoint = `/api/activities/activities?zaak=${mainZaakUrl}`;
    return this.http.Get<Activity[]>(endpoint);
  }

  /**
   * Patch activity.
   * @param id
   * @param formData
   * @returns {Observable<any>}
   */
  patchActivity(id, formData): Observable<any> {
    return this.http.Patch<any>(encodeURI(`/api/activities/activities/${id}`), formData);
  }

  /**
   * Delete activity.
   * @param id
   * @returns {Observable<any>}
   */
  deleteActivity(id): Observable<any> {
    return this.http.Delete<any>(encodeURI(`/api/activities/activities/${id}`));
  }

  /**
   * Create new activity.
   * @param formData
   * @returns {Observable<any>}
   */
  postNewActivity(formData): Observable<any> {
    return this.http.Post<any>(encodeURI('/api/activities/activities'), formData);
  }

  /**
   * Create note for activity.
   * @param formData
   * @returns {Observable<any>}
   */
  postNotes(formData): Observable<any> {
    return this.http.Post<any>(encodeURI('/api/activities/events'), formData);
  }

  /**
   * Open document
   * @param endpoint
   * @returns {Observable<ReadWriteDocument>}
   */
  readDocument(endpoint) {
    return this.http.Post<ReadWriteDocument>(endpoint);
  }

}
