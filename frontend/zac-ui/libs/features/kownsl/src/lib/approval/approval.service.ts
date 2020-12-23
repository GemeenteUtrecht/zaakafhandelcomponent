import { Injectable } from '@angular/core';
import { ApplicationHttpClient } from '@gu/services';
import { Observable } from 'rxjs';
import { ApprovalForm } from '../../models/approval-form';
import { ReviewRequest } from '../../models/review-request';
import { HttpResponse } from '@angular/common/http';

@Injectable({
  providedIn: 'root'
})
export class ApprovalService {

  constructor(private http: ApplicationHttpClient) { }

  getApproval(uuid: string): Observable<HttpResponse<ReviewRequest>> {
    const endpoint = encodeURI(`/kownsl/review-requests/${uuid}/approval`);
    const options = {
      observe: 'response' as 'response'
    }
    return this.http.Get<ReviewRequest>(endpoint, options);
  }

  postApproval(formData: ApprovalForm, uuid:string): Observable<any> {
    return this.http.Post<ApprovalForm>(encodeURI(`/kownsl/review-requests/${uuid}/approval`), formData);
  }
}
