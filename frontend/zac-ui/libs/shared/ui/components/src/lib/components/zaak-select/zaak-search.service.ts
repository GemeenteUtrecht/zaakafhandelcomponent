import {HttpResponse} from "@angular/common/http";
import {Injectable} from '@angular/core';
import {Observable} from "rxjs";
import {ApplicationHttpClient} from "@gu/services";

@Injectable()
export class ZaakSearchService {
  constructor(private http: ApplicationHttpClient) {
  }

  /**
   * Creates a request for suggestions for cases partially matching indentifier `query`.
   * @param {string} query
   */
  autocomplete(query: string): Observable<HttpResponse<any>> {
    const endpoint = encodeURI(`/api/search/zaken/autocomplete?identificatie=${query}`);
    return this.http.Get<any>(endpoint);
  }

  /**
   * Given results `suggestions` from `this.autocomplete()`, returns the data as (select) choices.
   * @param suggestions
   */
  suggestionsAsChoices(suggestions): Array<{ label: string, value: string }> {
    return suggestions.map((suggestion) => ({
      label: suggestion.identificatie,
      value: suggestion,
    }));
  }
}
