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
  isLoading: boolean;
  bronorganisatie: string;
  identificatie: string;

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
    this.getInformation().subscribe(data => {
      this.data = data;
      this.isLoading = false;
    }, error => {
      console.log(error);
      this.isLoading = false;
    })
  }

  getInformation(): Observable<HttpResponse<any>> {
    const endpoint = encodeURI(`/core/cases/${this.bronorganisatie}/${this.identificatie}`);
    return this.http.Get<ReviewRequest>(endpoint);
  }

}
