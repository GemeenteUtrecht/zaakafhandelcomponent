import {Injectable} from '@angular/core';
import {Observable} from 'rxjs';
import {User} from '@gu/models';
import {ApplicationHttpClient} from '@gu/services';
import {Activity} from '../models/activity';

@Injectable({
  providedIn: 'root'
})
export class FeaturesZaakDetailService {

  constructor(private http: ApplicationHttpClient) {
  }

  getActivities(zaakUrl): Observable<Activity[]> {
    const endpoint = `/activities/api/activities?zaak=${zaakUrl}`;
    return this.http.Get<Activity[]>(endpoint);
  }

  getCurrentUser(): Observable<User> {
    const endpoint = encodeURI("/api/accounts/users/me");
    return this.http.Get<User>(endpoint);
  }

  postAccessRequest(formData): Observable<any> {
    const endpoint = encodeURI("/api/accounts/access-requests");
    return this.http.Post<any>(endpoint, formData);
  }
}
