import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ZaaktypeEigenschap } from '@gu/models';
import { ApplicationHttpClient } from '@gu/services';
import { Search } from '../models/search';
import { ReportQuery } from '../models/report';


@Injectable({
  providedIn: 'root'
})
export class SearchService {

  constructor(private http: ApplicationHttpClient) { }

  getZaaktypeEigenschappen(zaaktypeUrl): Observable<ZaaktypeEigenschap[]> {
    const endpoint = encodeURI(`/api/core/eigenschappen?zaaktype=${zaaktypeUrl}`);
    return this.http.Get<ZaaktypeEigenschap[]>(endpoint);
  }

  /**
   * Retrieve a list of zaken based on input data. The response contains only zaken the user has permissions to see.
   * @param {Search} search
   * @param {number} page
   * @param {string | null} ordering
   * @returns {Observable<any>}
   */
  searchZaken(search: Search, page: number, ordering?: string|null): Observable<any> {
    const pageValue = `?page=${page}`;
    const query = ordering ? `&ordering=${ordering}` : '';
    const endpoint = encodeURI(`/api/search/zaken${pageValue}${query}`);
    return this.http.Post<any>(endpoint, search);
  }

  postCreateReport(formData: ReportQuery): Observable<any> {
    const endpoint = encodeURI('/api/search/reports/');
    return this.http.Post<any>(endpoint, formData);
  }
}
