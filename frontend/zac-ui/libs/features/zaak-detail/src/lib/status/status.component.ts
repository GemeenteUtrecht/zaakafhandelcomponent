import { Component, Input, OnInit } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpResponse } from '@angular/common/http';
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
  ) { }

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.bronorganisatie = params['bronorganisatie'];
      this.identificatie = params['identificatie'];

      this.isLoading = true;

      this.getStatuses().subscribe(data => {
        this.data = data;
        this.isLoading = false;
      }, error => {
        console.log(error);
        this.isLoading = false;
      })
    });
  }

  getStatuses(): Observable<HttpResponse<any>> {
    const endpoint = encodeURI(`/api/core/cases/${this.bronorganisatie}/${this.identificatie}/statuses`);
    return this.http.Get<any>(endpoint);
  }
}
