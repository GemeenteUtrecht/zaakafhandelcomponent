import { Injectable } from '@angular/core';
import { ApplicationHttpClient } from '@gu/services';
import { Observable } from 'rxjs';
import { ApprovalForm } from '../../models/approval-form';
import { HttpResponse } from '@angular/common/http';
import { Zaak } from '@gu/models';

@Injectable({
  providedIn: 'root'
})
export class ApprovalService {

  constructor(private http: ApplicationHttpClient) { }

  getApproval(uuid: string): Observable<HttpResponse<any>> {
    const endpoint = encodeURI(`/api/kownsl/review-requests/${uuid}/approval`);
    const options = {
      observe: 'response' as 'response'
    }
    return this.http.Get<any>(endpoint, options);
  }

  getZaakDetail(bronorganisatie: string, identificatie: string): Observable<Zaak> {
    return this.http.Get<Zaak>(encodeURI(`/api/core/cases/${bronorganisatie}/${identificatie}`));
  }

  postApproval(formData: ApprovalForm, uuid:string): Observable<any> {
    return this.http.Post<ApprovalForm>(encodeURI(`/api/kownsl/review-requests/${uuid}/approval`), formData);
  }
}
