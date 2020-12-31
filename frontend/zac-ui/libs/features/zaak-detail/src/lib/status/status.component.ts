import { Component, Input, OnInit } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpResponse } from '@angular/common/http';
import { ReviewRequest } from '../../../../kownsl/src/models/review-request';
import { ApplicationHttpClient } from '@gu/services';
import { ActivatedRoute } from '@angular/router';
import { DatePipe } from '@angular/common';

@Component({
  selector: 'gu-status',
  templateUrl: './status.component.html',
  styleUrls: ['./status.component.scss']
})
export class StatusComponent implements OnInit {
  @Input() progress: number;
  @Input() deadline: string;

  data: any;
  isLoading: boolean;
  bronorganisatie: string;
  identificatie: string;

  pipe = new DatePipe("nl-NL");

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
    this.getStatuses().subscribe(data => {
      console.log(data);
      this.data = data;
    }, error => {
      console.log(error);
    })
  }

  getStatuses(): Observable<HttpResponse<any>> {
    const endpoint = encodeURI(`/core/cases/${this.bronorganisatie}/${this.identificatie}/statuses`);
    return this.http.Get<ReviewRequest>(endpoint);
  }
}
