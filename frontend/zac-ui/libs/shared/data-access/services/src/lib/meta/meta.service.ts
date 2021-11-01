import {Injectable} from '@angular/core';
import {Observable} from 'rxjs';
import {ApplicationHttpClient} from '@gu/services';
import {CachedObservableMethod} from '@gu/utils';
import {MetaConfidentiality} from '@gu/models';

@Injectable({
  providedIn: 'root',
})
export class MetaService {
  constructor(private http: ApplicationHttpClient) {
  }

  /**
   * List the available confidentiality classification.
   * @return {Observable}
   */
  @CachedObservableMethod('MetaService.listConfidentialityClassifications')
  listConfidentialityClassifications(): Observable<MetaConfidentiality[]> {
    const endpoint = encodeURI('/api/core/vertrouwelijkheidsaanduidingen');
    return this.http.Get<MetaConfidentiality[]>(endpoint);
  }
}
