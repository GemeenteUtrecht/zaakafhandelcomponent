import {Injectable} from '@angular/core';
import {ApplicationHttpClient} from '@gu/services';
import { Observable } from 'rxjs';


@Injectable({
  providedIn: 'root'
})
export class PingService {

  constructor(
    private http: ApplicationHttpClient
  ) {
  }

  /**
   * Ping server to show activity
   * @return {Observable}
   */
  pingServer(): Observable<any> {
    const endpoint = encodeURI(`/api/ping/`);
    return this.http.Get<any>(endpoint);
  }

}
