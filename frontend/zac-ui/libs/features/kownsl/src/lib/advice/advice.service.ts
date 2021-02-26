import { Injectable } from '@angular/core';
import { ApplicationHttpClient } from '@gu/services';
import { Observable } from 'rxjs';
import { AdviceForm } from '../../models/advice-form';
import { ReviewRequest } from '../../models/review-request';
import { HttpResponse } from '@angular/common/http';
import { Document, ReadWriteDocument } from '../../../../zaak-detail/src/lib/documenten/documenten.interface';

@Injectable({
  providedIn: 'root'
})
export class AdviceService {

  constructor(private http: ApplicationHttpClient) { }

  getAdvice(uuid: string): Observable<HttpResponse<any>> {
    const endpoint = encodeURI(`/api/kownsl/review-requests/${uuid}/advice`);
    const options = {
      observe: 'response' as 'response'
    }
    return this.http.Get<any>(endpoint, options);
  }

  postAdvice(formData: AdviceForm, uuid: string): Observable<AdviceForm> {
    return this.http.Post<AdviceForm>(encodeURI(`/api/kownsl/review-requests/${uuid}/advice`), formData);
  }

  readDocument(bronorganisatie: string, identificatie: string): Observable<ReadWriteDocument> {
    const endpoint = encodeURI(`/api/dowc/${bronorganisatie}/${identificatie}/read`);
    return this.http.Post<ReadWriteDocument>(endpoint);
  }

  openDocumentEdit(bronorganisatie: string, identificatie: string): Observable<ReadWriteDocument> {
    const endpoint = encodeURI(`/api/dowc/${bronorganisatie}/${identificatie}/write`);
    return this.http.Post<ReadWriteDocument>(endpoint);
  }

  closeDocumentEdit(endpoint: string): Observable<any> {
    endpoint = encodeURI(endpoint);
    return this.http.Delete<any>(endpoint);
  }

}
