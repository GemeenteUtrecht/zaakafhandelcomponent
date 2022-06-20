import {Injectable} from '@angular/core';
import {ApplicationHttpClient} from '@gu/services';
import {Observable} from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class CreateCaseService {

  constructor(private http: ApplicationHttpClient) {
  }

  /**
   * Request the case url with process instsance.
   */
  getZaakUrlForProcessInstance(instanceId): Observable<any> {
    const endpoint = encodeURI(`/api/camunda/fetch-process-instances/${instanceId}/zaak`);
    return this.http.Get<any>(endpoint);
  }
}
