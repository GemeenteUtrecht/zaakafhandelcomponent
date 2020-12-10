import { Injectable } from '@angular/core';
import { ApplicationHttpClient } from '@gu/services';
import { Observable } from 'rxjs';
import { ApprovalForm } from '../../models/approval-form';

@Injectable({
  providedIn: 'root'
})
export class ApprovalService {

  constructor(private http: ApplicationHttpClient) { }

  getApproval(): Observable<any> {
    return this.http.Get<any>(encodeURI('/kownsl/review-requests/mock/approval'));
  }

  postApproval(formData: ApprovalForm): Observable<any> {
    return this.http.Post<ApprovalForm>(encodeURI('/kownsl/review-requests/mock/approval'), formData);
  }
}
