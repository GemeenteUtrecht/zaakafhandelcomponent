import {HttpParams, HttpResponse} from "@angular/common/http";
import {Injectable} from '@angular/core';
import {Router} from '@angular/router';
import {Observable} from 'rxjs';
import {Document, RelatedCase, EigenschapWaarde, UserPermission, Zaak, NieuweEigenschap} from '@gu/models';
import {ApplicationHttpClient} from '@gu/services';
import {CachedObservableMethod, ClearCacheOnMethodCall, isTestEnvironment} from '@gu/utils';
import {MapGeometry} from "../../../../../ui/components/src/lib/components/map/map";


@Injectable({
  providedIn: 'root'
})
export class ZaakService {

  constructor(
    private http: ApplicationHttpClient,
    private router: Router) {
  }

  /**
   * Navigate to a case.
   * @param {{bronorganisatie: string, identificatie: string}} zaak
   */
  navigateToCase(zaak: { bronorganisatie: string, identificatie: string }) {
    this.router.navigate(['zaken', zaak.bronorganisatie, zaak.identificatie]);
  }

  /**
   * Retrieve case details.
   * @param {string} bronorganisatie
   * @param {string} identificatie
   * @return {Observable}
   */
  @CachedObservableMethod('ZaakService.retrieveCaseDetails')
  retrieveCaseDetails(bronorganisatie: string, identificatie: string): Observable<Zaak> {
    return this.http.Get<Zaak>(encodeURI(`/api/core/cases/${bronorganisatie}/${identificatie}`));
  }

  /**
   * Update case details.
   * @param {string} bronorganisatie
   * @param {string} identificatie
   * @param {*} formData
   * @return {Observable}
   */
  @ClearCacheOnMethodCall('ZaakService.retrieveCaseDetails')
  updateCaseDetails(bronorganisatie, identificatie, formData): Observable<any> {
    const endpoint = encodeURI(`/api/core/cases/${bronorganisatie}/${identificatie}`);
    return this.http.Patch<any>(endpoint, formData);
  }

  /**
   * Edit case document.
   * @param {string} bronorganisatie
   * @param {string} identificatie
   * @param {*} formData
   * @return {Observable}
   */
  @ClearCacheOnMethodCall('ZaakService.retrieveCaseDetails')
  editCaseDocument(bronorganisatie, identificatie, formData: any): Observable<any> {
    const endpoint = encodeURI(`/api/core/cases/${bronorganisatie}/${identificatie}/document`);
    return this.http.Patch<any>(endpoint, formData);
  }

  /**
   * List case documents.
   * @param {string} bronorganisatie
   * @param {string} identificatie
   * @return {Observable}
   */
  listCaseDocuments(bronorganisatie, identificatie): Observable<Document[]> {
    const endpoint = encodeURI(`/api/core/cases/${bronorganisatie}/${identificatie}/documents`);
    return this.http.Get<Document[]>(endpoint);
  }

  /**
   * List case properties.
   * @param {string} bronorganisatie
   * @param {string} identificatie
   * @return {Observable}
   */
  listCaseProperties(bronorganisatie, identificatie): Observable<any> {
    const endpoint = encodeURI(`/api/core/cases/${bronorganisatie}/${identificatie}/properties`);
    return this.http.Get<any>(endpoint);
  }

  /**
   * Update case property
   * @param {EigenschapWaarde} property
   * @return {Observable}
   */
  @ClearCacheOnMethodCall('ZaakService.retrieveCaseDetails')
  updateCaseProperty(property: EigenschapWaarde):Observable<any> {
    const endpoint = encodeURI(`/api/core/cases/properties`);
    const params = new HttpParams().set('url', property.url)
    const waarde = property.waarde;
    if (!waarde) {
      return this.http.Delete(endpoint, {
        params: params
      })
    }

    return this.http.Patch(endpoint, {
      waarde: waarde,
    }, {
      params: params,
    })
  }

  /**
   * Create case property
   * @param {NieuweEigenschap} newProperty
   */
  @ClearCacheOnMethodCall('ZaakService.retrieveCaseDetails')
  createCaseProperty(newProperty: NieuweEigenschap) {
    const endpoint = encodeURI(`/api/core/cases/properties`);
    return this.http.Post(endpoint, newProperty)
  }

  /**
   * List case users and atomic permissions.
   * @param {string} bronorganisatie
   * @param {string} identificatie
   * @return {Observable}
   */
  listCaseUsers(bronorganisatie: string, identificatie: string): Observable<UserPermission[]> {
    const endpoint = encodeURI(`/api/core/cases/${bronorganisatie}/${identificatie}/atomic-permissions`);
    return this.http.Get<UserPermission[]>(endpoint);
  }

  @CachedObservableMethod('ZaakService.listRelatedCases')
  listRelatedCases(bronorganisatie: string, identificatie: string): Observable<RelatedCase[]> {
    const endpoint = encodeURI(`/api/core/cases/${bronorganisatie}/${identificatie}/related-cases`);
    return this.http.Get<RelatedCase[]>(endpoint);
  }

  /**
   * Relates a case (zaak) to another case (zaak).
   * @param {Object} data
   */
  @ClearCacheOnMethodCall('ZaakService.listRelatedCases')
  addRelatedCase(data: { relationZaak: string, aardRelatie: string, mainZaak: string }): Observable<{ relationZaak: string, aardRelatie: string, mainZaak: string }> {
    return this.http.Post<{ relationZaak: string, aardRelatie: string, mainZaak: string }>(encodeURI("/api/core/cases/related-case"), data);
  }

  /**
   * List related objects of a case.
   * @param {string} bronorganisatie
   * @param {string} identificatie
   * @return {Observable}
   */
  @CachedObservableMethod('ZaakService.listRelatedObjects')
  listRelatedObjects(bronorganisatie: string, identificatie: string): Observable<any> {
    const endpoint = encodeURI(`/api/core/cases/${bronorganisatie}/${identificatie}/objects`);
    return this.http.Get<any>(endpoint);
  }

  /**
   * Create an access request.
   * Access request for a particular zaak.
   * @param {{zaak: {bronorganisatie: string, identificatie: string}, comment: string}} formData
   * @return {Observable}
   */
  createAccessRequest(formData): Observable<any> {
    const endpoint = encodeURI("/api/accounts/access-requests");
    return this.http.Post<any>(endpoint, formData);
  }

  /**
   * Searches zaken (cases) based on identificatie.
   * @param {string} identificatie (Partial) identificatie of zaak (case).
   * @return {Observable}
   */
  searchZaken(identificatie: string): Observable<Zaak[]> {
    const endpoint = encodeURI(`/api/search/zaken/autocomplete?identificatie=${identificatie}`);
    return this.http.Get<Zaak[]>(endpoint);
  }

  /**
   * Converts a case (zaak) to a MapGeometry, ready to draw on the map.
   * @param {Zaak} zaak
   * @param {Object} options
   */
  zaakToMapGeometry(zaak: Zaak, options: Object = {}): MapGeometry {
    const mapGeometry = {
      title: zaak.identificatie,
      geometry: zaak.zaakgeometrie,
    }

    if (mapGeometry) {
      Object.assign(mapGeometry, options);
    }
    return mapGeometry;
  }

  /**
   * Form the URL to case in Tezza.
   * @param {Zaak} zaak
   */
  createTezzaUrl(zaak: Zaak): string {
    const zaakUuid = zaak.url.split('/api/v1/zaken/')[1]; // Extract case uuid from open zaak url
    const tezzaHost = isTestEnvironment() ? 'https://alfresco-tezza.cg-intern.ont.utrecht.nl' : 'https://alfresco-tezza.cg-intern.acc.utrecht.nl';
    return `${tezzaHost}/#/details/cases/${zaakUuid}`;
  }

}
