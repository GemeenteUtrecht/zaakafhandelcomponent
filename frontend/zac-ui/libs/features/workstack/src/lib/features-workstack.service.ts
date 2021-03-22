import { Injectable } from '@angular/core';
import { ApplicationHttpClient } from '@gu/services';
import { forkJoin, Observable } from 'rxjs';
import { Tab } from './constants/tabs';

@Injectable({
  providedIn: 'root'
})
export class FeaturesWorkstackService {

  constructor(private http: ApplicationHttpClient) { }

  getWorkstack(tabs: Tab[]): Observable<any> {
    const observables = [];
    tabs.forEach(tab => {
      const endpoint = encodeURI(tab.endpoint);
      observables.push(this.http.Get<any>(endpoint));
    });
    return forkJoin(observables)
  }
}
