import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import {ReadWriteDocument} from "@gu/models";
import { ApplicationHttpClient } from '@gu/services';

@Injectable({
  providedIn: 'root'
})
export class DocumentenService {

  constructor(private http: ApplicationHttpClient) { }

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
}
