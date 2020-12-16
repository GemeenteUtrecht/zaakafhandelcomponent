import { Injectable } from '@angular/core';
import { ApplicationHttpClient } from '@gu/services';
import { Observable } from 'rxjs';
import { AdviceForm } from '../../models/advice-form';
import { ReviewRequest } from '../../models/review-request';

@Injectable({
  providedIn: 'root'
})
export class AdviceService {

  constructor(private http: ApplicationHttpClient) { }

  getAdvice(uuid: string): Observable<ReviewRequest> {
    return this.http.Get<ReviewRequest>(encodeURI(`/kownsl/review-requests/${uuid}/advice`));
  }

  postAdvice(formData: AdviceForm, uuid: string): Observable<AdviceForm> {
    return this.http.Post<AdviceForm>(encodeURI(`/kownsl/review-requests/${uuid}/advice`), formData);
  }

}
