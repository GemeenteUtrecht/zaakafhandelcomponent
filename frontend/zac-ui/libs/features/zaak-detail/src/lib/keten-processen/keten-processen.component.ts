import { Component, Input, OnInit } from '@angular/core';
import { ApplicationHttpClient } from '@gu/services';
import { ActivatedRoute } from '@angular/router';
import { Observable } from 'rxjs';
import { HttpClient, HttpHeaders, HttpResponse } from '@angular/common/http';
import { DatePipe } from '@angular/common';

@Component({
  selector: 'gu-keten-processen',
  templateUrl: './keten-processen.component.html',
  styleUrls: ['./keten-processen.component.scss']
})
export class KetenProcessenComponent implements OnInit {

  @Input() zaakUrl: string;
  data: any;
  isLoading = true;
  bronorganisatie: string;
  identificatie: string;

  pipe = new DatePipe("nl-NL");

  constructor(
    private http: HttpClient,
    private customHttp: ApplicationHttpClient,
    private route: ActivatedRoute
  ) {
    this.route.paramMap.subscribe( params => {
      this.bronorganisatie = params.get('bronorganisatie');
      this.identificatie = params.get('identificatie');
    });
  }

  ngOnInit(): void {
    this.isLoading = true;
    this.getProcesses().subscribe( data => {
      this.data = data;
      this.isLoading = false;
    }, error => {
      console.log(error);
      this.isLoading = false;
    })
  }

  getProcesses(): Observable<any> {
    const endpoint = encodeURI(`/camunda/api/camunda/fetch-process-instances?zaak_url=${this.zaakUrl}`);
    return this.http.get(endpoint);
  }

  sendMessage(value) {
    const endpoint = encodeURI("/core/_send-message");
    const headers = new HttpHeaders().set('Content-Type', 'application/json');
    const options = {
      headers: headers,
      withCredentials: true,
    }
    this.http.post(endpoint, {"message": value}, options).subscribe( res => {
      console.log(res);
    })
  }

  redirect(url) {
    window.open(url,"_self")
  }

}
