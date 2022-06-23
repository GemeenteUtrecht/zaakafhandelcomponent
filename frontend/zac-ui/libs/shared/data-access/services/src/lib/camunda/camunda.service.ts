import {Injectable} from '@angular/core';
import {ApplicationHttpClient} from '@gu/services';
import {Observable} from 'rxjs';
import { ProcessInstanceCase } from '@gu/models';

@Injectable({
  providedIn: 'root'
})
export class CamundaService {

  constructor(private http: ApplicationHttpClient) {
  }

  /**
   * Request the case url with process instance.
   * @param instanceId
   * @returns {Observable<ProcessInstanceCase>}
   */
  getCaseUrlForProcessInstance(instanceId): Observable<ProcessInstanceCase> {
    const endpoint = encodeURI(`/api/camunda/fetch-process-instances/${instanceId}/zaak`);
    return this.http.Get<ProcessInstanceCase>(endpoint);
  }
}
