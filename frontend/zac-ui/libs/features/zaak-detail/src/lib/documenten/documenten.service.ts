import { Injectable } from '@angular/core';
import { ApplicationHttpClient } from '@gu/services';
import { Observable } from 'rxjs';
import { HttpResponse } from '@angular/common/http';
import { ReadWriteDocument } from './documenten.interface';
import { Document } from './documenten.interface';

@Injectable({
  providedIn: 'root'
})
export class DocumentenService {

  constructor(private http: ApplicationHttpClient) { }

  getDocuments(bronorganisatie, identificatie): Observable<Document[]> {
    const endpoint = encodeURI(`/api/core/cases/${bronorganisatie}/${identificatie}/documents`);
    return this.http.Get<Document[]>(endpoint);
  }

  readDocument(readUrl: string): Observable<ReadWriteDocument> {
    const endpoint = encodeURI(readUrl);
    return this.http.Post<ReadWriteDocument>(endpoint);
  }

  openDocumentEdit(writeUrl: string): Observable<ReadWriteDocument> {
    const endpoint = encodeURI(writeUrl);
    return this.http.Post<ReadWriteDocument>(endpoint);
  }

  closeDocumentEdit(deleteUrl: string): Observable<any> {
    const endpoint = encodeURI(deleteUrl);
    return this.http.Delete<any>(endpoint);
  }

  getConfidentiality(): Observable<any> {
    const endpoint = encodeURI("/api/core/vertrouwelijkheidsaanduidingen");
    return this.http.Get<any>(endpoint);
  }

  patchConfidentiality(bronorganisatie, identificatie, formData): Observable<any> {
    const endpoint = encodeURI(`/api/core/cases/${bronorganisatie}/${identificatie}/document`);
    return this.http.Patch<any>(endpoint, formData);
  }
}
