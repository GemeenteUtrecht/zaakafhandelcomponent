import {Injectable} from '@angular/core';
import {
  HttpErrorResponse,
  HttpEvent,
  HttpHandler,
  HttpInterceptor,
  HttpRequest,
} from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { Router } from '@angular/router';
import { ApplicationHttpClient } from '@gu/services';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {

  readonly NOT_LOGGED_IN_MESSAGE = "Authenticatiegegevens zijn niet opgegeven.";

  constructor(
    private router: Router,
    private http: ApplicationHttpClient
  ) { }

  private checkAuthentication(error: HttpErrorResponse): boolean {
    return error.status && error.status === 403 && error.error.detail === this.NOT_LOGGED_IN_MESSAGE;
  }

  private checkAzureSession(error: HttpErrorResponse): boolean {
    console.log(error.error);
    return error.status && error.status === 403 && error.error['refresh_url']
  }

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    return next.handle(req)
      .pipe(
        catchError((error, caught) => {
          if (error instanceof HttpErrorResponse) {
            if (this.checkAuthentication(error)) {
              const currentPath = this.router.url;
              window.location.href = `/accounts/login/?next=/ui${currentPath}`;
              return throwError(error);
            } else if (this.checkAzureSession(error)) {
              const refreshUrl = error.error['refresh_url'];
              this.http.Get(refreshUrl);
              return throwError(error);
            } else {
              return throwError(error);
            }
          }
          return caught;
        })
      )
  }
}
