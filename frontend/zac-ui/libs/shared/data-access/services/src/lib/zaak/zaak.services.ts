import {Injectable} from '@angular/core';
import {Observable} from 'rxjs';
import {ApplicationHttpClient} from '@gu/services';
import {Document, UserPermission, Zaak} from '@gu/models';

@Injectable({
  providedIn: 'root'
})
export class ZaakService {

  constructor(private http: ApplicationHttpClient) {
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
