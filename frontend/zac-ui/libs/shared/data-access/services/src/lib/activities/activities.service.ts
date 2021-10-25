import {Injectable} from '@angular/core';
import {Observable} from 'rxjs';
import {ApplicationHttpClient} from '@gu/services';
import {Activity, User} from '@gu/models';

@Injectable({
  providedIn: 'root'
})
export class ActivitiesService {

  constructor(private http: ApplicationHttpClient) {
  }

  getActivities(zaakUrl): Observable<Activity[]> {
    const endpoint = `/activities/api/activities?zaak=${zaakUrl}`;
    return this.http.Get<Activity[]>(endpoint);
  }
}
