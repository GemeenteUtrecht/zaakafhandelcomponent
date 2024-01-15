import {Injectable} from '@angular/core';
import {ApplicationHttpClient} from '@gu/services';
import { Observable } from 'rxjs';


@Injectable({
  providedIn: 'root'
})
export class HealthService {

  constructor(
    private http: ApplicationHttpClient
  ) {
  }

  /**
   * Check application health
   * @return {Observable}
   */
  getHealth(): Observable<any> {
    const endpoint = encodeURI(`/api/_health/`);
    return this.http.Get<any>(endpoint);
  }

}
