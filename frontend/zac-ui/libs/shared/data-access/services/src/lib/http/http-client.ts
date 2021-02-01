import {HttpClient, HttpHeaders, HttpParams} from '@angular/common/http';
import {Injectable} from '@angular/core';
import {Observable} from 'rxjs';

export interface IRequestOptions {
  headers?: HttpHeaders;
  observe?: any;
  params?: HttpParams;
  reportProgress?: boolean;
  responseType?: any;
  withCredentials?: boolean;
  body?: any;
}

export function applicationHttpClientCreator(http: HttpClient) {
  return new ApplicationHttpClient(http);
}

@Injectable({
  providedIn: 'root'
})
export class ApplicationHttpClient {

  public constructor(public http: HttpClient) {}

  public Get<T>(endPoint: string, options?: IRequestOptions): Observable<any> {
    return this.http.get<T>(endPoint, options);
  }

  public Post<T>(endPoint: string, params?: object, options?: IRequestOptions): Observable<any> {
    const headers = new HttpHeaders().set('Content-Type', 'application/json');
    options = {
      headers: headers,
      withCredentials: true
    }
    return this.http.post<T>(endPoint, params, options);
  }

  public Put<T>(endPoint: string, params: object, options?: IRequestOptions): Observable<any> {
    return this.http.put<T>(endPoint, params, options);
  }

  public Delete<T>(endPoint: string, options?: IRequestOptions): Observable<any> {
    options = {
      withCredentials: true
    }
    return this.http.delete<T>(endPoint, options);
  }
}
