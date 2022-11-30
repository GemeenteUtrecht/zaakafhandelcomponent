import {Injectable} from '@angular/core';
import {Observable} from 'rxjs';
import {ApplicationHttpClient} from '@gu/services';
import {CachedObservableMethod} from '@gu/utils';
import {MetaConfidentiality, ZaaktypeEigenschap, MetaZaaktype, MetaRoltype, MetaZaaktypeCatalogus} from '@gu/models';

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

  /**
   * Retrieve case type properties by providing catalog and description
   * @param catalogus
   * @param identificatie
   * @returns {Observable<ZaaktypeEigenschap[]>}
   */
  getZaaktypeEigenschappenByCatalogus(catalogus, identificatie): Observable<ZaaktypeEigenschap[]> {
    const endpoint = encodeURI(`/api/core/eigenschappen?catalogus=${catalogus}&zaaktype_identificatie=${identificatie}`);
    return this.http.Get<ZaaktypeEigenschap[]>(endpoint);
  }

  /**
   * Retrieve case type properties by providing url
   * @param zaaktypeUrl
   * @returns {Observable<ZaaktypeEigenschap[]>}
   */
  getZaaktypeEigenschappenByUrl(zaaktypeUrl): Observable<ZaaktypeEigenschap[]> {
    const endpoint = encodeURI(`/api/core/eigenschappen?zaaktype=${zaaktypeUrl}`);
    return this.http.Get<ZaaktypeEigenschap[]>(endpoint);
  }

  /**
   * Retrieve a collection of case types
   * @param {boolean} activeCasesOnly
   * @returns {Observable<MetaZaaktype>}
   */
  getCaseTypes(activeCasesOnly = false): Observable<MetaZaaktype> {
    const endpoint = encodeURI(`/api/core/zaaktypen${activeCasesOnly ? '?active=true' : ''}`);
    return this.http.Get<MetaZaaktype>(endpoint);
  }

  /**
   * Retrieve a collection of case types
   * @param {string} domain
   * @returns {Observable<MetaZaaktype>}
   */
  getCaseTypesForDomain(domain: string): Observable<MetaZaaktype> {
    const endpoint = encodeURI(`/api/core/zaaktypen?domein=${domain}`);
    return this.http.Get<MetaZaaktype>(endpoint);
  }

  /**
   * Retrieve a collection of role types
   * @returns {Observable<MetaRoltype>}
   */
  getRoleTypes(zaak): Observable<MetaRoltype[]> {
    const endpoint = encodeURI(`/api/core/roltypes?zaak=${zaak}`);
    return this.http.Get<MetaRoltype[]>(endpoint);
  }
}
