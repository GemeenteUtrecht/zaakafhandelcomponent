import { Injectable } from '@angular/core';
import { ApplicationHttpClient } from '@gu/services';
import { forkJoin, Observable, of } from 'rxjs';
import { AdviceForm } from '../../models/advice-form';
import { HttpResponse } from '@angular/common/http';
import { DocumentUrls, ReadWriteDocument } from '../../../../zaak-detail/src/lib/documenten/documenten.interface';
import { CloseDocument } from '../../models/close-document';
import { Zaak } from '@gu/models';

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

  getZaakDetail(bronorganisatie: string, identificatie: string): Observable<Zaak> {
    return this.http.Get<Zaak>(encodeURI(`/api/core/cases/${bronorganisatie}/${identificatie}`));
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
