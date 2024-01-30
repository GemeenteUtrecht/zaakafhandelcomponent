import {HttpParams, HttpResponse} from "@angular/common/http";
import {Injectable} from '@angular/core';
import {Router} from '@angular/router';
import {Observable} from 'rxjs';
import {
  RelatedCase,
  EigenschapWaarde,
  UserPermission,
  Zaak,
  NieuweEigenschap,
  CreateCase, ProcessInstance, CreateBetrokkene, CreateCaseDocument, Betrokkene, ListDocuments, Oudbehandelaren
} from '@gu/models';
import {ApplicationHttpClient} from '@gu/services';
import {CachedObservableMethod, ClearCacheOnMethodCall, getEnv} from '@gu/utils';
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
   * Navigate to actions of a case.
   * @param {{bronorganisatie: string, identificatie: string}} zaak
   */
  navigateToCaseActions(zaak: { bronorganisatie: string, identificatie: string }) {
    this.router.navigate(['zaken', zaak.bronorganisatie, zaak.identificatie, 'acties']);
  }

  /**
   * Create a new case.
   * @param {CreateCase} formData
   * @returns {Observable<ProcessInstance>}
   */
  createCase(formData: CreateCase): Observable<ProcessInstance> {
    const endpoint = encodeURI(`/api/core/cases`);
    return this.http.Post<ProcessInstance>(endpoint, formData);
  }

  /**
   * Start process for case.
   * @param {string} bronorganisatie
   * @param {string} identificatie
   * @returns {Observable<ProcessInstance>}
   */
  startCaseProcess(bronorganisatie: string, identificatie: string): Observable<ProcessInstance> {
    const endpoint = encodeURI(`/api/core/cases/${bronorganisatie}/${identificatie}/start-process`);
    return this.http.Post<ProcessInstance>(endpoint);
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
   * Edit case document.
   * @param {CreateCaseDocument} formData
   * @return {Observable}
   */
  @ClearCacheOnMethodCall('ZaakService.retrieveCaseDetails')
  createCaseDocument(formData: any): Observable<any> {
    const endpoint = encodeURI(`/api/core/cases/document`);
    return this.http.Post<any>(endpoint, formData);
  }

  /**
   * List case documents.
   * @param {string} bronorganisatie
   * @param {string} identificatie
   * @param {number} page
   * @param {string} sortData
   * @return {Observable}
   */
  listCaseDocuments(bronorganisatie, identificatie, page, sortData): Observable<ListDocuments> {
    const pageValue = page ? `?page=${page}` : '';
    const sortOrder = sortData?.order === 'desc' ? '-' : '';
    const sortValue = sortData ? sortData.value?.toLowerCase() : '';
    const sortParameter = sortData ? `&ordering=${sortOrder}${sortValue}` : '';
    const endpoint = encodeURI(`/api/search/cases/${bronorganisatie}/${identificatie}/documents${pageValue}${sortParameter}`);
    return this.http.Post<ListDocuments>(endpoint);
  }


  /**
   * List task documents.
   * @param {string} url
   * @param {number} page
   * @param {string} sortValue
   * @return {Observable}
   */
  listTaskDocuments(url, page, sortData): Observable<ListDocuments> {
    const pageValue = page ? `?page=${page}` : '';
    const sortOrder = sortData?.order === 'desc' ? '-' : '';
    const sortValue = sortData ? sortData.value?.toLowerCase() : '';
    const sortParameter = sortData ? `&ordering=${sortOrder}${sortValue}` : '';
    const endpoint = encodeURI(`${url}${pageValue}${sortParameter}`);
    return this.http.Post<ListDocuments>(endpoint);
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

    return this.http.Patch(endpoint, {
      waarde: waarde ? waarde : '-',
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
   * Deletes a case relation.
   * @param {Object} data
   */
  deleteRelatedCase(formData) {
    const endpoint = encodeURI("/api/core/cases/related-case");
    return this.http.Delete<any>(endpoint, formData)
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
    const tezzaHost = getEnv('ALFRESCO_PREVIEW_URL', 'https://alfresco-tezza.cg-intern.ont.utrecht.nl/');
    return `${tezzaHost}/#/details/cases/${zaakUuid}`;
  }

  /**
   * Create link for zaak.
   * @param zaak
   * @returns {string}
   */
  createCaseUrl(zaak: Zaak) {
    return `/zaken/${zaak.bronorganisatie}/${zaak.identificatie}`;
  }

  /**
   * Create a role.
   * @param {string} bronorganisatie
   * @param {string} identificatie
   * @param {CreateBetrokkene} caseRole
   * @returns {Observable<*>}
   */
  @ClearCacheOnMethodCall('ZaakService.retrieveCaseDetails')
  createCaseRole(bronorganisatie: string, identificatie: string, caseRole: CreateBetrokkene): Observable<any> {
    const endpoint = encodeURI(`/api/core/cases/${bronorganisatie}/${identificatie}/roles`);
    return this.http.Post<any>(endpoint, caseRole);
  }

  /**
   * Retrieve all roles
   * @param {string} bronorganisatie
   * @param {string} identificatie
   * @returns {Observable<Betrokkene[]>}
   */
  getCaseRoles(bronorganisatie: string, identificatie: string): Observable<Betrokkene[]> {
    const endpoint = encodeURI(`/api/core/cases/${bronorganisatie}/${identificatie}/roles`);
    return this.http.Get<Betrokkene[]>(endpoint);
  }

  /**
   * Retrieve all oud behandelaren
   * @param {string} bronorganisatie
   * @param {string} identificatie
   * @returns {Observable<Oudbehandelaren>}
   */
  getCaseOudbehandelaren(bronorganisatie: string, identificatie: string): Observable<Oudbehandelaren> {
    const endpoint = encodeURI(`/api/oudbehandelaren/oudbehandelaren/${bronorganisatie}/${identificatie}`);
    return this.http.Get<Oudbehandelaren>(endpoint);
  }

  /**
   * Deletes a role
   * @param {string} bronorganisatie
   * @param {string} identificatie
   * @param {string} url
   * @returns {Observable<*>}
   */
  deleteCaseRole(bronorganisatie: string, identificatie: string, url: string): Observable<any> {
    const endpoint = encodeURI(`/api/core/cases/${bronorganisatie}/${identificatie}/roles?url=${url}`);
    return this.http.Delete<any>(endpoint);
  }

  /**
   * Patch zaak url to api
   * @param url
   * @returns {Observable<any>}
   */
  updateRecentlyViewedCase(url) {
    const formData = {zaak: url}
    const endpoint = encodeURI('/api/core/recently-viewed');
    return this.http.Patch<any>(endpoint, formData);
  }

}
