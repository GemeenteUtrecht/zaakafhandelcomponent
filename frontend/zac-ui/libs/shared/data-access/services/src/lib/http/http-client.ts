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
  public Get<T>(endPoint: string, options?: IRequestOptions): Observable<T> {
    return this.http.get<T>(endPoint, options);
  }

  public Post<T>(endPoint: string, params?: any, options?: IRequestOptions): Observable<T> {
    options = { withCredentials: true, ...options }
    return this.http.post<T>(endPoint, params, options);
  }

  public Put<T>(endPoint: string, params?: any, options?: IRequestOptions): Observable<T> {
    options = { withCredentials: true, ...options }
    return this.http.put<T>(endPoint, params, options);
  }

  public Patch<T>(endPoint: string, params?: any, options?: IRequestOptions): Observable<T> {
    options = { withCredentials: true, ...options }
    return this.http.patch<T>(endPoint, params, options);
  }

  public Delete<T>(endPoint: string, params?: any, options?: IRequestOptions): Observable<T> {
    options = { withCredentials: true, body: params, ...options }
    return this.http.delete<T>(endPoint, options);
  }
}
