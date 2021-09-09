import {HttpParams} from "@angular/common/http";
import {Injectable} from '@angular/core';
import {Router} from '@angular/router';
import {Observable} from 'rxjs';
import {Document, EigenschapWaarde, UserPermission, Zaak} from '@gu/models';
import {ApplicationHttpClient} from '@gu/services';

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
  navigateToCase(zaak: {bronorganisatie: string, identificatie: string}) {
    this.router.navigate(['zaken', zaak.bronorganisatie, zaak.identificatie]);
  }

  /**
   * Retrieve case details.
   * @param {string} bronorganisatie
   * @param {string} identificatie
   * @return {Observable}
   */
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
   */
  updateCaseProperty(property: EigenschapWaarde) {
    const endpoint = encodeURI(`/api/core/cases/properties`);
    const params = new HttpParams().set('url', property.url)
    return this.http.Patch(endpoint, {
      value: property.value,
    }, {
      params: params,
    })
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

  /**
   * List related objects of a case.
   * @param {string} bronorganisatie
   * @param {string} identificatie
   * @return {Observable}
   */
  listRelatedObjects(bronorganisatie: string, identificatie: string): Observable<any> {
      const endpoint = encodeURI(`/api/core/cases/${bronorganisatie}/${identificatie}/objects`);
      return this.http.Get<any>(endpoint);
  }
}
