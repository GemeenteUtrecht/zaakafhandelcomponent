import {Injectable} from '@angular/core';
import {forkJoin, Observable, of} from 'rxjs';
import {catchError} from 'rxjs/operators';
import {ApplicationHttpClient} from '@gu/services';
import {Tab} from './constants/tabs';

@Injectable({
  providedIn: 'root',
})
export class FeaturesWorkstackService {
  constructor(private http: ApplicationHttpClient) {}

  /**
   * Receive all workstack tabs.
   * @param {Tab[]} tabs
   * @param {number} page
   * @returns {Observable<any>}
   */
  getWorkstack(tabs: Tab[], page: number = 1): Observable<any> {
    const observables = [];
    const pageValue = `?page=${page}`;
    tabs.forEach((tab) => {
      const endpoint = encodeURI(`${tab.endpoint}${pageValue}`);
      observables.push(this.http.Get<any>(endpoint).pipe(catchError(error => of(error))));
    });
    return forkJoin(observables);
  }

  /**
   * Get sorted work stack cases.
   * @param sortValue
   * @param sortOrder
   * @returns {Observable<any>}
   */
  getWorkstackZaken(sortValue, sortOrder): Observable<any> {
    const order = sortOrder === 'desc' ? '-' : '';
    let endpoint = '/api/workstack/cases';

    if(sortValue) {
      endpoint += encodeURI(
        `?ordering=${order}${sortValue}`
      );
    }
    return this.http.Get<any>(endpoint);
  }

  /**
   * Get sorted work stack reviews.
   * @param sortValue
   * @param sortOrder
   * @returns {Observable<any>}
   */
  getWorkstackReview(sortValue, sortOrder): Observable<any> {
    const order = sortOrder === 'desc' ? '-' : '';
    let endpoint = '/api/workstack/review-requests';

    if(sortValue) {
      endpoint += encodeURI(
        `?ordering=${order}${sortValue}`
      );
    }
    return this.http.Get<any>(endpoint);
  }

}
