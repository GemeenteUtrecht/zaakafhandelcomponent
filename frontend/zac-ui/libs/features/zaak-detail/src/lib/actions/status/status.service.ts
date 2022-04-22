import {Injectable} from '@angular/core';
import {ApplicationHttpClient} from '@gu/services';
import {Observable} from 'rxjs';
import { HttpResponse } from '@angular/common/http';
import { BoardItem } from '@gu/models';


@Injectable({
  providedIn: 'root'
})
export class StatusService {
  constructor(private http: ApplicationHttpClient) {
  }

  /**
   * Retrieve zaak statuses
   * @param bronorganisatie
   * @param identificatie
   * @returns {Observable<HttpResponse<any>>}
   */
  getZaakStatuses(bronorganisatie, identificatie): Observable<HttpResponse<any>> {
    const endpoint = encodeURI(`/api/core/cases/${bronorganisatie}/${identificatie}/statuses`);
    return this.http.Get<any>(endpoint);
  }

  /**
   * Retrieve dashboard statuses
   * @param zaakUrl
   * @returns {Observable<BoardItem[]>}
   */
  getDashboardStatus(zaakUrl): Observable<BoardItem[]>  {
    const endpoint = encodeURI(`/api/dashboard/items?zaak=${zaakUrl}`);
    return this.http.Get<BoardItem[]>(endpoint);
  }

  /**
   * Update dashboard status
   * @param uuid
   * @param formData
   * @returns {Observable<BoardItem>}
   */
  updateBoardItem(uuid, formData): Observable<BoardItem> {
    const endpoint = `/api/dashboard/items/${uuid}`;
    return this.http.Put<BoardItem>(endpoint, formData);
  }
}
