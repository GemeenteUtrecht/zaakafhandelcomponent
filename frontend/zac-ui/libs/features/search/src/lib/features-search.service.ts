import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApplicationHttpClient } from '@gu/services';
import { ZaaktypeEigenschap } from '../models/zaaktype-eigenschappen';
import { Zaaktype } from '../models/zaaktype';
import { Search } from '../models/search';
import { TableSort, Zaak } from '@gu/models';
import { tableHeadMapping } from './search-results/constants/table';

@Injectable({
  providedIn: 'root'
})
export class FeaturesSearchService {

  constructor(private http: ApplicationHttpClient) { }

  getZaaktypen(): Observable<Zaaktype> {
    const endpoint = encodeURI("/api/core/zaaktypen");
    return this.http.Get<Zaaktype>(endpoint);
  }

  getZaaktypeEigenschappen(catalogus, zaaktype_omschrijving): Observable<ZaaktypeEigenschap[]> {
    const endpoint = encodeURI(`/api/core/eigenschappen?catalogus=${catalogus}&zaaktype_omschrijving=${zaaktype_omschrijving}`);
    return this.http.Get<ZaaktypeEigenschap[]>(endpoint);
  }

  postSearchZaken(formData: Search, sortData?: TableSort): Observable<Zaak[]> {
    const sortOrder = sortData?.order === 'desc' ? '-' : '';
    const sortValue = sortData ? tableHeadMapping[sortData.value] : '';
    const sortParameter = sortData ? `?ordering=${sortOrder}${sortValue}` : '';
    const endpoint = encodeURI(`/api/search/zaken${sortParameter}`);
    return this.http.Post<Zaak[]>(endpoint, formData);
  }
}
