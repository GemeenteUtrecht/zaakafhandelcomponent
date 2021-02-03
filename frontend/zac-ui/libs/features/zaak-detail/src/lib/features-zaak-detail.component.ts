import { Component, OnInit } from '@angular/core';
import { ApplicationHttpClient } from '@gu/services';
import { ActivatedRoute } from '@angular/router';
import { Observable } from 'rxjs';
import { HttpResponse } from '@angular/common/http';
import { ReviewRequest } from '../../../kownsl/src/models/review-request';

@Component({
  selector: 'gu-features-zaak-detail',
  templateUrl: './features-zaak-detail.component.html',
  styleUrls: ['./features-zaak-detail.component.scss']
})
export class FeaturesZaakDetailComponent implements OnInit {
  data: any;
  bronorganisatie: string;
  identificatie: string;
  mainZaakUrl: string;

  isLoading: boolean;
  hasError: boolean;
  errorMessage: string;

  constructor(
    private http: ApplicationHttpClient,
    private route: ActivatedRoute
  ) {
    this.route.paramMap.subscribe( params => {
      this.bronorganisatie = params.get('bronorganisatie');
      this.identificatie = params.get('identificatie');
    });
  }

  ngOnInit(): void {
    this.fetchInformation();
  }

  fetchInformation() {
    this.isLoading = true;
    this.getInformation().subscribe(data => {
      this.data = data;
      this.mainZaakUrl = data.url ? data.url : null;
      this.isLoading = false;
    }, errorResponse => {
      this.hasError = true;
      this.errorMessage = errorResponse.error.detail;
      this.isLoading = false;
    })
  }

  getInformation(): Observable<HttpResponse<any>> {
    const endpoint = encodeURI(`/api/core/cases/${this.bronorganisatie}/${this.identificatie}`);
    return this.http.Get<ReviewRequest>(endpoint);
  }

}
