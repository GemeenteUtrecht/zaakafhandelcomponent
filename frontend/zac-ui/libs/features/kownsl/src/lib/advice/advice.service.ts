import { Injectable } from '@angular/core';
import { ApplicationHttpClient } from '@gu/services';
import { Observable } from 'rxjs';
import { AdviceForm } from '../../models/advice-form';

@Injectable({
  providedIn: 'root'
})
export class AdviceService {

  constructor(private http: ApplicationHttpClient) { }

  getAdvice(): Observable<any> {
    return this.http.Get<any>(encodeURI('/kownsl/review-requests/mock/advice'));
  }

  postAdvice(formData: AdviceForm): Observable<any> {
    return this.http.Post<AdviceForm>(encodeURI('/kownsl/review-requests/mock/advice'), formData);
  }

}
