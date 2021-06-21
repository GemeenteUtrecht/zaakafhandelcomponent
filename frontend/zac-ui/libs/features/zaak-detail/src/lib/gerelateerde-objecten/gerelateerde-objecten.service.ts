import { Injectable } from '@angular/core';
import {ApplicationHttpClient} from "@gu/services";
import {Observable} from "rxjs";

@Injectable({
  providedIn: 'root'
})
export class GerelateerdeObjectenService {

  constructor(private http: ApplicationHttpClient) { }

  getRelatedObjects(bronorganisatie: string, identificatie: string): Observable<any> {
      const endpoint = encodeURI(`/api/core/cases/${bronorganisatie}/${identificatie}/objects`);
      return this.http.Get<any>(endpoint);
  }
}
