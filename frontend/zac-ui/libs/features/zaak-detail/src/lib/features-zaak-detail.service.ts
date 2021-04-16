import { Injectable } from '@angular/core';
import { ApplicationHttpClient } from '@gu/services';
import { Observable } from 'rxjs';
import { User, Zaak } from '@gu/models';
import { Activity } from '../models/activity';

@Injectable({
  providedIn: 'root'
})
export class FeaturesZaakDetailService {

  constructor(private http: ApplicationHttpClient) { }

  getInformation(bronorganisatie, identificatie): Observable<Zaak> {
    const endpoint = encodeURI(`/api/core/cases/${bronorganisatie}/${identificatie}`);
    return this.http.Get<Zaak>(endpoint);
  }

  getActivities(zaakUrl): Observable<Activity[]> {
    const endpoint = `/activities/api/activities?zaak=${zaakUrl}`;
    return this.http.Get<Activity[]>(endpoint);
  }

  getCurrentUser(): Observable<User> {
    const endpoint = encodeURI("/api/accounts/users/me");
    return this.http.Get<User>(endpoint);
  }

}
