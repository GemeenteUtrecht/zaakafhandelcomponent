import { Injectable } from '@angular/core';
import { ApplicationHttpClient } from '@gu/services';
import { forkJoin, Observable, of } from 'rxjs';
import { AdviceForm } from '../../models/advice-form';
import {HttpParams, HttpResponse} from '@angular/common/http';
import { CloseDocument } from '../../models/close-document';
import {DocumentUrls, ReadWriteDocument} from "@gu/models";
import { ReviewRequest } from '@gu/kownsl';

@Injectable({
  providedIn: 'root'
})
export class AdviceService {

  constructor(private http: ApplicationHttpClient) { }

  getAdvice(uuid: string, assignee: string): Observable<ReviewRequest> {
    const endpoint = encodeURI(`/api/kownsl/review-requests/${uuid}/advice`);
    const options = {
      params: new HttpParams().set('assignee', assignee),
    }
    return this.http.Get<any>(endpoint, options);
  }

  postAdvice(formData: AdviceForm, uuid: string, assignee: string): Observable<AdviceForm> {
    return this.http.Post<AdviceForm>(encodeURI(`/api/kownsl/review-requests/${uuid}/advice?assignee=${assignee}`), formData);
  }

  readDocument(bronorganisatie: string, identificatie: string, zaakUrl: string): Observable<ReadWriteDocument> {
    const body = { zaak: zaakUrl };
    const endpoint = encodeURI(`/api/dowc/${bronorganisatie}/${identificatie}/read`);
    return this.http.Post<ReadWriteDocument>(endpoint, body);
  }

  openDocumentEdit(bronorganisatie: string, identificatie: string, zaakUrl: string): Observable<ReadWriteDocument> {
    const body = { zaak: zaakUrl };
    const endpoint = encodeURI(`/api/dowc/${bronorganisatie}/${identificatie}/write`);
    return this.http.Post<ReadWriteDocument>(endpoint, body);
  }

  closeDocumentEdit(deleteUrls: DocumentUrls[]): Observable<any> {
    if (deleteUrls.length > 0) {
      const observables = [];
      deleteUrls.forEach(doc => {
        const endpoint = encodeURI(doc.deleteUrl);
        observables.push(this.http.Delete<CloseDocument>(endpoint));
      });
      return forkJoin(observables)
    } else {
      return of(true);
    }
  }

}
