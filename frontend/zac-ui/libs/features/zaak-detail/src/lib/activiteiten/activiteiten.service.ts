import { Injectable } from '@angular/core';
import { ApplicationHttpClient } from '@gu/services';
import { Observable } from 'rxjs';
import { Activity } from '../../models/activity';
import { UserSearch } from '../../models/user-search';

@Injectable({
  providedIn: 'root'
})
export class ActiviteitenService {

  constructor(private http: ApplicationHttpClient) { }

  getAccounts(searchInput: string): Observable<UserSearch> {
    const endpoint = encodeURI(`/api/accounts/users?search=${searchInput}`);
    return this.http.Get<UserSearch>(endpoint);
  }

  getActivities(mainZaakUrl): Observable<Activity[]> {
    const endpoint = `/activities/api/activities?zaak=${mainZaakUrl}`;
    return this.http.Get<Activity[]>(endpoint);
  }

  patchActivity(id, formData): Observable<any> {
    return this.http.Patch<any>(encodeURI(`/activities/api/activities/${id}`), formData);
  }

  deleteActivity(id): Observable<any> {
    return this.http.Delete<any>(encodeURI(`/activities/api/activities/${id}`));
  }

  postNewActivity(formData): Observable<any> {
    return this.http.Post<any>(encodeURI('/activities/api/activities'), formData);
  }

  postNotes(formData): Observable<any> {
    return this.http.Post<any>(encodeURI('/activities/api/events'), formData);
  }

}
