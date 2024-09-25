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
    const endpoint = encodeURI(`/api/camunda/process-instances/${instanceId}/zaak`);
    return this.http.Get<ProcessInstanceCase>(endpoint);
  }

  /**
   * Update user task.
   * @param {string} taskId
   * @param formData
   * @returns {Observable<*>}
   */
  updateUserTask(taskId: string, formData: any) {
    const endpoint = encodeURI(`/api/camunda/task-data/${taskId}`);
    return this.http.Put<any>(endpoint, formData);
  }

  /**
   * Update main behandelaar
   * @param formData
   * @returns {Observable<*>}
   */
  changeBehandelaar(formData) {
    const endpoint = encodeURI(`/api/camunda/change-behandelaar`);
    return this.http.Post<any>(endpoint, formData);
  }
}
