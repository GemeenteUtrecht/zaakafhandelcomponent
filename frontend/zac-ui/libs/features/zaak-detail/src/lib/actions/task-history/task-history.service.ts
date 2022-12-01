import {HttpParams} from '@angular/common/http';
import {Injectable} from '@angular/core';
import {Observable} from 'rxjs';
import {ApplicationHttpClient} from '@gu/services';
import {HistoricalUserTaskData} from './historical-user-task-data';


@Injectable({
  providedIn: 'root'
})
export class TaskHistoryService {
  constructor(private http: ApplicationHttpClient) {
  }

  /**
   * Retrieve the historical user task data of the ZAAK.
   * @param {string} zaakUrl
   * @return {Observable}
   */
  retrieveHistoricalUserTaskDataOfZaak(zaakUrl): Observable<HistoricalUserTaskData[]> {
    const endpoint = encodeURI(`/api/camunda/task-data/historical`);
    const params = new HttpParams().set('zaakUrl', zaakUrl)
    return this.http.Get<HistoricalUserTaskData[]>(endpoint, {params: params});
  }
}
