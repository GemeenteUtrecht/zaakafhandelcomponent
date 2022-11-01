import {Injectable} from '@angular/core';
import {Observable} from 'rxjs';
import {ApplicationHttpClient} from '@gu/services';
import {LandingPage} from '../models/landing-page';


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
}
