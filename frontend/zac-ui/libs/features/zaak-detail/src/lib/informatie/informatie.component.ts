import { Component, Input, OnInit } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpResponse } from '@angular/common/http';
import { DatePipe } from '@angular/common';
import { ApplicationHttpClient } from '@gu/services';
import { ActivatedRoute } from '@angular/router';
import { ReviewRequest } from '../../../../kownsl/src/models/review-request';

@Component({
  selector: 'gu-informatie',
  templateUrl: './informatie.component.html',
  styleUrls: ['./informatie.component.scss']
})
export class InformatieComponent implements OnInit {

  @Input() infoData: any;
  propertiesData: any;
  isLoading = true;
  bronorganisatie: string;
  identificatie: string;

  constructor(
    private http: ApplicationHttpClient,
    private route: ActivatedRoute
  ) { }

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.bronorganisatie = params['bronorganisatie'];
      this.identificatie = params['identificatie'];

      this.isLoading = true;
      this.getProperties().subscribe(data => {
        this.propertiesData = data;
        this.isLoading = false;
      }, error => {
        console.log(error);
        this.isLoading = false;
      })
    })
  }

  getProperties(): Observable<HttpResponse<any>> {
    const endpoint = encodeURI(`/api/core/cases/${this.bronorganisatie}/${this.identificatie}/properties`);
    return this.http.Get<any>(endpoint);
  }
}
