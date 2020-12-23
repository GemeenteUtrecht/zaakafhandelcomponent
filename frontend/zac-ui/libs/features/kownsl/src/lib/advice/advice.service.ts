import { Injectable } from '@angular/core';
import { ApplicationHttpClient } from '@gu/services';
import { Observable } from 'rxjs';
import { AdviceForm } from '../../models/advice-form';
import { ReviewRequest } from '../../models/review-request';
import { HttpResponse } from '@angular/common/http';

@Injectable({
  providedIn: 'root'
})
export class AdviceService {

  constructor(private http: ApplicationHttpClient) { }

  getAdvice(uuid: string): Observable<HttpResponse<ReviewRequest>> {
    const endpoint = encodeURI(`/kownsl/review-requests/${uuid}/advice`);
    const options = {
      observe: 'response' as 'response'
    }
    return this.http.Get<ReviewRequest>(endpoint, options);
  }

  postAdvice(formData: AdviceForm, uuid: string): Observable<AdviceForm> {
    return this.http.Post<AdviceForm>(encodeURI(`/kownsl/review-requests/${uuid}/advice`), formData);
  }

}
