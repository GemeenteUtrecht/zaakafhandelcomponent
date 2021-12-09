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

  getWorkstack(tabs: Tab[]): Observable<any> {
    const observables = [];
    tabs.forEach((tab) => {
      const endpoint = encodeURI(tab.endpoint);
      observables.push(this.http.Get<any>(endpoint).pipe(catchError(error => of(error))));
    });
    return forkJoin(observables);
  }

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

  patchAccessRequest(requestId, formData): Observable<any> {
    const endpoint = encodeURI(`/api/accounts/access-requests/${requestId}`);
    return this.http.Patch<any>(endpoint, formData);
  }

}
