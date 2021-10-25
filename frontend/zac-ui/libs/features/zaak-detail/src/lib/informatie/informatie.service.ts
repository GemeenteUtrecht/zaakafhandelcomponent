import { Injectable } from '@angular/core';
import { ApplicationHttpClient } from '@gu/services';
import { Observable } from 'rxjs';
import {CachedObservableMethod} from '@gu/utils';

@Injectable({
  providedIn: 'root'
})
export class InformatieService {

  constructor(private http: ApplicationHttpClient) { }

  /**
   * FIXME
   */
  @CachedObservableMethod('/api/core/vertrouwelijkheidsaanduidingen')
  getConfidentiality(): Observable<any> {
    const endpoint = encodeURI("/api/core/vertrouwelijkheidsaanduidingen");
    return this.http.Get<any>(endpoint);
  }
}
