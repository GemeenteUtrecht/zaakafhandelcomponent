import {Injectable} from '@angular/core';
import {Observable} from 'rxjs';
import {ApplicationHttpClient} from '@gu/services';
import {HttpParams} from '@angular/common/http';

@Injectable({
  providedIn: 'root',
})
export class KadasterService {
  constructor(private http: ApplicationHttpClient) {
  }

  /**
   * Retrieve pand from BAG API.
   * @param {string} id The ID of the BAG object. Can be found using the BAG address suggestions.
   */
  retrievePand(id: string): Observable<any> {
    const params = new HttpParams().set('id', id);
    return this.http.Get(`/api/kadaster/adres/pand`, {params});
  }

  /**
   * Retrieve pand from BAG API.
   * @param {string} pandidentificatie The pandidentificatie of the BAG object
   */
  retrievePandByPandId(pandidentificatie) {
    return this.http.Get(`/api/kadaster/panden/${pandidentificatie}`, );
  }

  /**
   * Retrieve verblijfsobject from BAG API.
   * @param {string} id The ID of the BAG object. Can be found using the BAG address suggestions.
   */
  retrieveVerblijfsObject(id: string): Observable<any> {
    const params = new HttpParams().set('id', id);
    return this.http.Get(`/api/kadaster/adres/verblijfsobject`, {params});
  }


  /**
   * List BAG address suggestions
   * @param {string} q The search query. The Solr-syntax can be used, for example: combining searches with and or using
   * double quotes for sequenced searches. Searches are allowed to be incomplete and you can use synonyms.
   * @return {Observable}
   */
  listBAGAddressSuggestions(q: string): Observable<any> {
    const params = new HttpParams().set('q', q);
    return this.http.Get(`/api/kadaster/autocomplete/adres`, {params});
  }
}

