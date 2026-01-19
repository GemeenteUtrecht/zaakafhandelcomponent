import { Injectable } from '@angular/core';
import { ApplicationHttpClient } from '@gu/services';
import { Observable } from 'rxjs';
import { ApprovalForm } from '../../models/approval-form';
import {HttpParams, HttpResponse} from '@angular/common/http';
import { ReviewRequest } from '@gu/kownsl';

@Injectable({
  providedIn: 'root'
})
export class ApprovalService {

  constructor(private http: ApplicationHttpClient) { }

  getApproval(uuid: string, assignee: string): Observable<ReviewRequest> {
    const endpoint = encodeURI(`/api/kownsl/review-requests/${uuid}/approval`);
    const options = {
      params: new HttpParams().set('assignee', assignee)
    }
    return this.http.Get<any>(endpoint, options);
  }

  postApproval(formData: ApprovalForm, uuid: string, assignee: string): Observable<any> {
    return this.http.Post<ApprovalForm>(encodeURI(`/api/kownsl/review-requests/${uuid}/approval?assignee=${assignee}`), formData);
  }
}
