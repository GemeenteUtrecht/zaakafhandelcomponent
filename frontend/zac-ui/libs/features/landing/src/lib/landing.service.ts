import {Injectable} from '@angular/core';
import {Observable} from 'rxjs';
import {ApplicationHttpClient} from '@gu/services';
import {LandingPage} from '../models/landing-page';
import { HttpResponse } from '@angular/common/http';


@Injectable({
  providedIn: 'root'
})
export class LandingService {
  constructor(private http: ApplicationHttpClient) {
  }

  /**
   * Retrieve the landing page configuration.
   * @return {Observable<LandingPage>}
   */
  landingPageRetrieve(): Observable<LandingPage> {
    const endpoint = encodeURI('/api/landing-page');
    return this.http.Get<LandingPage>(endpoint);
  }

  /**
   * Retrieve quick search results.
   * @param {string} query
   */
  quickSearch(query: string): Observable<HttpResponse<any>> {
    const body = { search: query };
    const endpoint = encodeURI(`/api/search/quick-search`);
    return this.http.Post<any>(endpoint, body);
  }

}
