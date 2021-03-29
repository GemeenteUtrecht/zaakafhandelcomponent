import { Component, Input, OnInit } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpResponse } from '@angular/common/http';
import { ApplicationHttpClient } from '@gu/services';
import { DatePipe } from '@angular/common';

@Component({
  selector: 'gu-status',
  templateUrl: './status.component.html',
  styleUrls: ['./status.component.scss']
})
export class StatusComponent implements OnInit {
  @Input() bronorganisatie: string;
  @Input() identificatie: string;
  @Input() progress: number;
  @Input() deadline: string;
  @Input() finished: boolean;

  data: any;
  isLoading: boolean;

  isExpanded = false;

  pipe = new DatePipe("nl-NL");

  constructor(
    private http: ApplicationHttpClient,
  ) { }

  ngOnInit(): void {
    this.isLoading = true;

    this.getStatuses().subscribe(data => {
      this.data = data;
      this.isLoading = false;
    }, error => {
      console.log(error);
      this.isLoading = false;
    })
  }

  getStatuses(): Observable<HttpResponse<any>> {
    const endpoint = encodeURI(`/api/core/cases/${this.bronorganisatie}/${this.identificatie}/statuses`);
    return this.http.Get<any>(endpoint);
  }
}
