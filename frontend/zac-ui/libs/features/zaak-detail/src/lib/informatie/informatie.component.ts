import { Component, Input, OnChanges } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpResponse } from '@angular/common/http';
import { ApplicationHttpClient } from '@gu/services';

@Component({
  selector: 'gu-informatie',
  templateUrl: './informatie.component.html',
  styleUrls: ['./informatie.component.scss']
})
export class InformatieComponent implements OnChanges {
  @Input() bronorganisatie: string;
  @Input() identificatie: string;
  @Input() infoData: any;

  propertiesData: any;
  isLoading = true;

  constructor(private http: ApplicationHttpClient) { }

  ngOnChanges(): void {
    this.isLoading = true;
    this.getProperties().subscribe(data => {
      this.propertiesData = data;
      this.isLoading = false;
    }, error => {
      console.log(error);
      this.isLoading = false;
    })
  }

  getProperties(): Observable<HttpResponse<any>> {
    const endpoint = encodeURI(`/api/core/cases/${this.bronorganisatie}/${this.identificatie}/properties`);
    return this.http.Get<any>(endpoint);
  }
}
