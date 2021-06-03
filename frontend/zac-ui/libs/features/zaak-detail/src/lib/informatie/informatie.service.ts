import { Injectable } from '@angular/core';
import { ApplicationHttpClient } from '@gu/services';
import { Observable } from 'rxjs';
import { HttpResponse } from '@angular/common/http';

@Injectable({
  providedIn: 'root'
})
export class InformatieService {

  constructor(private http: ApplicationHttpClient) { }

  getConfidentiality(): Observable<any> {
    const endpoint = encodeURI("/api/core/vertrouwelijkheidsaanduidingen");
    return this.http.Get<any>(endpoint);
  }

  getProperties(bronorganisatie, identificatie): Observable<any> {
    const endpoint = encodeURI(`/api/core/cases/${bronorganisatie}/${identificatie}/properties`);
    return this.http.Get<any>(endpoint);
  }

  patchConfidentiality(bronorganisatie, identificatie, formData): Observable<any> {
    const endpoint = encodeURI(`/api/core/cases/${bronorganisatie}/${identificatie}`);
    return this.http.Patch<any>(endpoint, formData);
  }

  patchCaseDetails(bronorganisatie, identificatie, formData): Observable<any> {
    const endpoint = encodeURI(`/api/core/cases/${bronorganisatie}/${identificatie}`);
    return this.http.Patch<any>(endpoint, formData);
  }
}
